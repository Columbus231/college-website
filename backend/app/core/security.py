from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def new_action_token() -> str:
    return secrets.token_urlsafe(32)


def hash_action_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(subject: str, token_version: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    issued_at = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": subject, "ver": token_version, "iat": issued_at, "exp": expires, "iss": settings.app_name},
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
