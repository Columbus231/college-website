import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import DbSession, current_user, get_email_service
from app.api.rate_limit import limiter
from app.core.config import settings
from app.core.email_service import EmailDeliveryError, EmailService
from app.core.roles import configure_role_permissions
from app.core.security import (
    create_access_token,
    hash_action_token,
    hash_password,
    new_action_token,
    verify_password,
)
from app.models import ApplicantProfile, EmailAction, Role, User
from app.schemas import (
    ActionTokenRequest,
    EmailTokenRequest,
    LoginRequest,
    MessageRead,
    PasswordResetRequest,
    RegisterRequest,
    TokenRead,
    UserRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
ACTION_LIFETIME = timedelta(minutes=30)
RESET_REQUEST_RESPONSE = "If an eligible account exists, an account email will be sent."


def _new_email_action(db: Session, user: User, purpose: Literal["verify_email", "reset_password"]) -> str:
    now = datetime.now(timezone.utc)
    db.execute(
        EmailAction.__table__.update()
        .where(
            EmailAction.user_id == user.id,
            EmailAction.purpose == purpose,
            EmailAction.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    raw_token = new_action_token()
    db.add(
        EmailAction(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_action_token(raw_token),
            expires_at=now + ACTION_LIFETIME,
        )
    )
    return raw_token


def _send_action_email(email_service: EmailService, recipient: str, purpose: str, token: str) -> None:
    try:
        email_service.send_action_link(recipient, purpose, token)
    except EmailDeliveryError:
        logger.warning("Account email delivery failed for purpose=%s", purpose)
        raise HTTPException(status_code=503, detail="Account email delivery is temporarily unavailable") from None


def _valid_action(db: Session, raw_token: str, purpose: str) -> EmailAction:
    action = db.scalar(
        select(EmailAction)
        .where(
            EmailAction.token_hash == hash_action_token(raw_token),
            EmailAction.purpose == purpose,
            EmailAction.consumed_at.is_(None),
        )
        .with_for_update()
    )
    if action is None:
        raise HTTPException(status_code=400, detail="This account link is invalid or expired")
    expiry = action.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This account link is invalid or expired")
    return action


@router.post("/register", response_model=MessageRead, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
def register(
    request: Request,
    body: RegisterRequest,
    db: DbSession,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> MessageRead:
    email = str(body.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        if not user.email_verified:
            token = _new_email_action(db, user, "verify_email")
            db.commit()
            _send_action_email(email_service, user.email, "verify_email", token)
        return MessageRead(message="If this address can be registered, a verification email will be sent.")

    applicant_role = db.scalar(select(Role).where(Role.name == "applicant"))
    if applicant_role is None:
        applicant_role = Role(name="applicant")
        db.add(applicant_role)
        db.flush()
    configure_role_permissions(db, applicant_role)
    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name)
    user.roles.append(applicant_role)
    user.applicant_profile = ApplicantProfile()
    db.add(user)
    try:
        db.flush()
        token = _new_email_action(db, user, "verify_email")
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        return MessageRead(message="If this address can be registered, a verification email will be sent.")
    _send_action_email(email_service, user.email, "verify_email", token)
    return MessageRead(message="If this address can be registered, a verification email will be sent.")


@router.post("/verify-email", response_model=MessageRead)
@limiter.limit("10/minute")
def verify_email(
    request: Request,
    body: ActionTokenRequest,
    db: DbSession,
) -> MessageRead:
    action = _valid_action(db, body.token, "verify_email")
    user = db.get(User, action.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="This account link is invalid or expired")
    now = datetime.now(timezone.utc)
    action.consumed_at = now
    user.email_verified = True
    db.execute(
        EmailAction.__table__.update()
        .where(
            EmailAction.user_id == user.id,
            EmailAction.purpose == "verify_email",
            EmailAction.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    db.commit()
    return MessageRead(message="Email address verified. You can now sign in.")


@router.post("/resend-verification", response_model=MessageRead, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/hour")
def resend_verification(
    request: Request,
    body: EmailTokenRequest,
    db: DbSession,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> MessageRead:
    user = db.scalar(select(User).where(User.email == str(body.email).lower(), User.is_active.is_(True)))
    if user is not None and not user.email_verified:
        token = _new_email_action(db, user, "verify_email")
        db.commit()
        _send_action_email(email_service, user.email, "verify_email", token)
    return MessageRead(message=RESET_REQUEST_RESPONSE)


@router.post("/login", response_model=TokenRead)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: DbSession) -> TokenRead:
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Verify your email address before signing in")
    return TokenRead(access_token=create_access_token(str(user.id), user.token_version))


@router.post("/password-reset/request", response_model=MessageRead, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/hour")
def request_password_reset(
    request: Request,
    body: EmailTokenRequest,
    db: DbSession,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> MessageRead:
    user = db.scalar(select(User).where(User.email == str(body.email).lower(), User.is_active.is_(True)))
    if user is not None and user.email_verified:
        token = _new_email_action(db, user, "reset_password")
        db.commit()
        try:
            email_service.send_action_link(user.email, "reset_password", token)
        except EmailDeliveryError:
            logger.warning("Account email delivery failed for purpose=reset_password")
    return MessageRead(message=RESET_REQUEST_RESPONSE)


@router.post("/password-reset/confirm", response_model=MessageRead)
@limiter.limit("10/minute")
def confirm_password_reset(
    request: Request,
    body: PasswordResetRequest,
    db: DbSession,
) -> MessageRead:
    action = _valid_action(db, body.token, "reset_password")
    user = db.get(User, action.user_id)
    if user is None or not user.is_active or not user.email_verified:
        raise HTTPException(status_code=400, detail="This account link is invalid or expired")
    now = datetime.now(timezone.utc)
    action.consumed_at = now
    user.password_hash = hash_password(body.password)
    user.token_version += 1
    db.execute(
        EmailAction.__table__.update()
        .where(
            EmailAction.user_id == user.id,
            EmailAction.purpose == "reset_password",
            EmailAction.consumed_at.is_(None),
        )
        .values(consumed_at=now)
    )
    db.commit()
    return MessageRead(message="Password updated. Sign in with your new password.")


@router.get("/me", response_model=UserRead)
def me(user: Annotated[User, Depends(current_user)]) -> UserRead:
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "roles": [role.name for role in user.roles]}
