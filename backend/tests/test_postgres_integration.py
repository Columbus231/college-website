import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.api.deps import get_email_service
from app.core.security import hash_password
from app.core.config import settings
from app.core.roles import configure_role_permissions
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Role, User

pytestmark = pytest.mark.postgres


class RecordingEmailService:
    def __init__(self):
        self.sent: list[dict[str, str]] = []

    def send_action_link(self, recipient: str, purpose: str, token: str) -> None:
        self.sent.append({"recipient": recipient, "purpose": purpose, "token": token})


@pytest.fixture(scope="module")
def postgres_client():
    test_url = os.getenv("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("Set TEST_DATABASE_URL to an explicitly disposable PostgreSQL test database")
    parsed_url = make_url(test_url)
    if parsed_url.get_backend_name() != "postgresql" or not (
        (parsed_url.database or "").endswith("_test")
        or parsed_url.host == "db-test"
    ):
        pytest.fail("PostgreSQL integration tests only run against a database explicitly named *_test or host db-test")
    if parsed_url != make_url(settings.database_url):
        pytest.fail("TEST_DATABASE_URL must exactly match DATABASE_URL so migrations and destructive tests use the same test database")
    assert engine.dialect.name == "postgresql"
    alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    with engine.begin() as connection:
        table_names = [table.name for table in Base.metadata.sorted_tables]
        if table_names:
            quoted_tables = ", ".join(engine.dialect.identifier_preparer.quote(name) for name in table_names)
            connection.execute(text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))

    with SessionLocal() as db:
        role = Role(name="admin")
        configure_role_permissions(db, role)
        db.add(User(
            email="postgres-admin@example.edu",
            password_hash=hash_password("postgres-admin-password-2026"),
            full_name="PostgreSQL Test Administrator",
            email_verified=True,
            roles=[role],
        ))
        db.commit()

    mailer = RecordingEmailService()
    app.dependency_overrides[get_email_service] = lambda: mailer
    app.state.test_email_service = mailer
    app.state.limiter.reset()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_email_service, None)
    del app.state.test_email_service
    app.state.limiter.reset()


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    result = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert result.status_code == 200
    return {"Authorization": f"Bearer {result.json()['access_token']}"}


def test_postgresql_migrated_schema_and_transactional_application_flow(postgres_client: TestClient):
    client = postgres_client
    assert client.get("/health").json() == {"status": "ok"}
    admin_headers = _login(client, "postgres-admin@example.edu", "postgres-admin-password-2026")
    program_response = client.post(
        "/api/v1/admin/programs",
        headers=admin_headers,
        json={"name": "PostgreSQL integration program", "level": "Undergraduate", "published": True},
    )
    assert program_response.status_code == 201
    program_id = program_response.json()["id"]

    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "postgres-applicant@example.edu", "password": "postgres-applicant-password-2026", "full_name": "PostgreSQL Applicant"},
    )
    assert registration.status_code == 202
    verification = client.app.state.test_email_service.sent[-1]
    assert client.post("/api/v1/auth/verify-email", json={"token": verification["token"]}).status_code == 200
    applicant_headers = _login(client, "postgres-applicant@example.edu", "postgres-applicant-password-2026")
    application = client.post(
        "/api/v1/applications",
        headers=applicant_headers,
        json={"program_id": program_id, "statement": "PostgreSQL transaction integration test"},
    )
    assert application.status_code == 201
    duplicate = client.post(
        "/api/v1/applications",
        headers=applicant_headers,
        json={"program_id": program_id},
    )
    assert duplicate.status_code == 409


def test_postgresql_applicant_privacy_and_role_authorization(postgres_client: TestClient):
    client = postgres_client
    assert client.get("/api/v1/applications/mine").status_code == 401
    applicant_headers = _login(client, "postgres-applicant@example.edu", "postgres-applicant-password-2026")
    assert client.get("/api/v1/admin/applications", headers=applicant_headers).status_code == 403
    assert client.get("/api/v1/applications/mine", headers=applicant_headers).status_code == 200
    admin_headers = _login(client, "postgres-admin@example.edu", "postgres-admin-password-2026")
    assert client.get("/api/v1/admin/applications", headers=admin_headers).status_code == 200
