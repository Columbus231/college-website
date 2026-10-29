import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_jwt_secret_is_required_to_be_strong_and_not_a_placeholder():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret_key="replace-with-a-random-secret-that-is-long-enough")


def test_production_settings_require_tls_email_scanning_and_shared_limits():
    production = Settings(
        _env_file=None,
        environment="production",
        jwt_secret_key=SecretStr("random-production-signing-key-with-adequate-entropy"),
        cors_origins=["https://college.example.edu"],
        public_app_url="https://college.example.edu",
        public_domain="college.example.edu",
        smtp_host="smtp.example.edu",
        smtp_username="college-mail",
        smtp_password=SecretStr("smtp-password-for-tests"),
        smtp_sender="noreply@example.edu",
        smtp_starttls=True,
        clamav_host="clamav",
        rate_limit_storage_uri="redis://:redis-password@redis:6379/0",
        database_url="postgresql+psycopg://user:password@db/college",
    )
    assert production.environment == "production"


def test_production_rejects_http_origins_and_missing_scanner():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key="random-production-signing-key-with-adequate-entropy",
            cors_origins=["http://college.example.edu"],
            public_app_url="http://college.example.edu",
            public_domain="college.example.edu",
            smtp_host="smtp.example.edu",
            smtp_username="college-mail",
            smtp_password="smtp-password-for-tests",
            smtp_sender="noreply@example.edu",
            smtp_starttls=True,
            rate_limit_storage_uri="redis://redis:6379/0",
        )


def test_production_rejects_unauthenticated_redis():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment="production",
            jwt_secret_key="random-production-signing-key-with-adequate-entropy",
            cors_origins=["https://college.example.edu"],
            public_app_url="https://college.example.edu",
            public_domain="college.example.edu",
            smtp_host="smtp.example.edu",
            smtp_username="college-mail",
            smtp_password="smtp-password-for-tests",
            smtp_sender="noreply@example.edu",
            smtp_starttls=True,
            clamav_host="clamav",
            rate_limit_storage_uri="redis://redis:6379/0",
            database_url="postgresql+psycopg://user:password@db/college",
        )
