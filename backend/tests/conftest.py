import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("JWT_SECRET_KEY", "isolated-test-only-key-with-adequate-length")

from app.api.deps import get_db, get_email_service
from app.core.security import hash_password
from app.core.roles import configure_role_permissions
from app.db import Base
from app.main import app
from app.models import Role, User


class RecordingEmailService:
    def __init__(self):
        self.sent: list[dict[str, str]] = []

    def send_action_link(self, recipient: str, purpose: str, token: str) -> None:
        self.sent.append({"recipient": recipient, "purpose": purpose, "token": token})


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with test_session() as db:
        applicant_role = Role(name="applicant")
        admin_role = Role(name="admin")
        admin = User(
            email="admin@example.edu",
            password_hash=hash_password("admin-test-password-2026"),
            full_name="Test Administrator",
            email_verified=True,
            roles=[admin_role],
        )
        configure_role_permissions(db, admin_role)
        db.add_all([applicant_role, admin_role, admin])
        db.commit()

    def override_get_db():
        with test_session() as db:
            yield db

    email_service = RecordingEmailService()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_email_service] = lambda: email_service
    app.state.test_email_service = email_service
    app.state.test_session = test_session
    app.state.limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.test_email_service
    del app.state.test_session
    app.state.limiter.reset()
    Base.metadata.drop_all(engine)
    engine.dispose()
