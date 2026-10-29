from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import EmailStr, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "College Website API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./college.db"
    jwt_secret_key: SecretStr
    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]
    public_app_url: str = "http://127.0.0.1:5173"
    public_domain: str = "localhost"
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_sender: EmailStr | None = None
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    smtp_timeout_seconds: int = Field(default=10, ge=1, le=60)
    clamav_host: str | None = None
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    clamav_timeout_seconds: int = Field(default=10, ge=1, le=60)
    rate_limit_storage_uri: str = "memory://"
    admin_email: EmailStr | None = None
    admin_password: str | None = None
    uploads_directory: str = "uploads"
    max_upload_bytes: int = Field(default=5_000_000, ge=1_024, le=50_000_000)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if (
            len(secret) < 32
            or "replace" in secret.lower()
            or "change-me" in secret.lower()
            or "development-only" in secret.lower()
        ):
            raise ValueError("JWT_SECRET_KEY must contain at least 32 characters")
        return value

    @model_validator(mode="after")
    def validate_deployment_settings(self):
        if self.smtp_ssl and self.smtp_starttls:
            raise ValueError("Configure either SMTP_SSL or SMTP_STARTTLS, not both")
        if self.environment == "production":
            origins = [urlsplit(origin) for origin in self.cors_origins]
            if any(
                origin.scheme != "https"
                or not origin.hostname
                or origin.path not in ("", "/")
                or origin.query
                or origin.fragment
                or origin.username
                or origin.password
                for origin in origins
            ):
                raise ValueError("Production CORS origins must use HTTPS")
            if not self.public_app_url.startswith("https://"):
                raise ValueError("Production public application URL must use HTTPS")
            app_host = urlsplit(self.public_app_url).hostname
            if not app_host or app_host.lower() != self.public_domain.lower() or app_host.lower() in {"localhost", "127.0.0.1"}:
                raise ValueError("Production public domain must match the configured public application URL")
            if not self.smtp_host or not self.smtp_sender or not self.smtp_username or not self.smtp_password:
                raise ValueError("Production requires configured authenticated SMTP email delivery")
            if not self.smtp_ssl and not self.smtp_starttls:
                raise ValueError("Production SMTP delivery must use TLS")
            if not self.clamav_host:
                raise ValueError("Production requires a configured ClamAV scanner")
            if not self.database_url.startswith(("postgresql://", "postgresql+")):
                raise ValueError("Production requires PostgreSQL")
            redis_url = urlsplit(self.rate_limit_storage_uri)
            if redis_url.scheme not in {"redis", "rediss"} or not redis_url.hostname or not redis_url.password:
                raise ValueError("Production rate limiting requires authenticated shared Redis storage")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
