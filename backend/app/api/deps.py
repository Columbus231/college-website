from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email_service import EmailService
from app.db import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[Session, Depends(get_db)]


def get_email_service() -> EmailService:
    return EmailService()


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=["HS256"],
            issuer=settings.app_name,
            options={"require": ["sub", "ver", "exp", "iat", "iss"]},
        )
        subject = payload.get("sub")
        user_id = int(subject)
        token_version = payload.get("ver")
        if not isinstance(token_version, int):
            raise ValueError("Invalid token version")
    except (jwt.PyJWTError, TypeError, ValueError):
        raise unauthorized from None
    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None or user.token_version != token_version:
        raise unauthorized
    return user


def require_roles(*allowed_roles: str):
    def role_dependency(user: Annotated[User, Depends(current_user)]) -> User:
        if not any(role.name in allowed_roles for role in user.roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return role_dependency


def require_permissions(*required_permissions: str):
    def permission_dependency(user: Annotated[User, Depends(current_user)]) -> User:
        user_permissions = {permission.name for role in user.roles for permission in role.permissions}
        if not set(required_permissions).issubset(user_permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return permission_dependency
