from pathlib import Path
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import update

from app.core.config import settings
from app.core.security import hash_action_token
from app.models import EmailAction

def register(client, email="applicant@example.edu"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "secure-test-password-2026", "full_name": "Test Applicant"},
    )
    matching = [
        item for item in client.app.state.test_email_service.sent
        if item["recipient"] == email and item["purpose"] == "verify_email"
    ]
    if matching:
        client.post("/api/v1/auth/verify-email", json={"token": matching[-1]["token"]})
    return response


def login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_and_openapi(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/openapi.json").status_code == 200


def test_registration_login_and_duplicate_protection(client):
    response = register(client)
    assert response.status_code == 202
    assert response.json()["message"]
    assert register(client).status_code == 202
    headers = login(client, "applicant@example.edu", "secure-test-password-2026")
    profile = client.get("/api/v1/auth/me", headers=headers).json()
    assert profile["email"] == "applicant@example.edu"
    assert profile["roles"] == ["applicant"]
    assert "password_hash" not in profile
    assert client.post("/api/v1/auth/login", json={"email": "applicant@example.edu", "password": "wrong-password"}).status_code == 401


def test_server_enforces_administrator_permissions(client):
    assert client.post("/api/v1/admin/programs", json={"name": "Test program", "level": "UG"}).status_code == 401
    register(client)
    applicant_headers = login(client, "applicant@example.edu", "secure-test-password-2026")
    response = client.post("/api/v1/admin/programs", headers=applicant_headers, json={"name": "Test program", "level": "UG"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_admin_can_publish_program_and_applicant_cannot_duplicate_application(client):
    admin_headers = login(client, "admin@example.edu", "admin-test-password-2026")
    created = client.post(
        "/api/v1/admin/programs",
        headers=admin_headers,
        json={"name": "Sample Engineering", "level": "Undergraduate", "published": True},
    )
    assert created.status_code == 201
    program_id = created.json()["id"]
    assert len(client.get("/api/v1/programs").json()) == 1

    register(client)
    applicant_headers = login(client, "applicant@example.edu", "secure-test-password-2026")
    application = client.post("/api/v1/applications", headers=applicant_headers, json={"program_id": program_id})
    assert application.status_code == 201
    assert application.json()["status"] == "draft"
    duplicate = client.post("/api/v1/applications", headers=applicant_headers, json={"program_id": program_id})
    assert duplicate.status_code == 409
    assert len(client.get("/api/v1/applications/mine", headers=applicant_headers).json()) == 1

    submitted = client.post(f"/api/v1/applications/{application.json()['id']}/submit", headers=applicant_headers)
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "submitted"

    updated = client.patch(
        f"/api/v1/admin/applications/{application.json()['id']}/status",
        headers=admin_headers,
        json={"status": "under_review"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "under_review"


def test_contact_submission_validation_and_admin_review(client):
    invalid = client.post("/api/v1/contact", json={"name": "A", "email": "bad", "message": "x"})
    assert invalid.status_code == 422
    accepted = client.post(
        "/api/v1/contact",
        json={"name": "Visitor Name", "email": "visitor@example.edu", "message": "Please send program details."},
    )
    assert accepted.status_code == 201
    admin_headers = login(client, "admin@example.edu", "admin-test-password-2026")
    submissions = client.get("/api/v1/admin/contact-submissions", headers=admin_headers)
    assert submissions.status_code == 200
    assert submissions.json()[0]["email"] == "visitor@example.edu"


def test_admin_can_assign_student_and_approve_faculty_but_cannot_grant_admin(client):
    admin_headers = login(client, "admin@example.edu", "admin-test-password-2026")
    applicant = register(client)
    applicant_id = client.get("/api/v1/auth/me", headers=login(client, "applicant@example.edu", "secure-test-password-2026")).json()["id"]
    denied = client.patch(
        f"/api/v1/admin/users/{applicant_id}/role",
        headers=admin_headers,
        json={"role": "admin"},
    )
    assert denied.status_code == 422

    assigned = client.patch(
        f"/api/v1/admin/users/{applicant_id}/role",
        headers=admin_headers,
        json={"role": "student", "student_number": "VERIFIED-001"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["roles"] == ["student"]

    faculty = register(client, "faculty@example.edu")
    faculty_id = client.get("/api/v1/auth/me", headers=login(client, "faculty@example.edu", "secure-test-password-2026")).json()["id"]
    assigned_faculty = client.patch(
        f"/api/v1/admin/users/{faculty_id}/role",
        headers=admin_headers,
        json={"role": "faculty", "designation": "Sample faculty"},
    )
    assert assigned_faculty.status_code == 200
    assert client.get("/api/v1/faculty").json() == []
    profiles = client.get("/api/v1/admin/faculty", headers=admin_headers).json()
    assert profiles[0]["approved"] is False
    approved = client.patch(f"/api/v1/admin/faculty/{profiles[0]['id']}/approve", headers=admin_headers)
    assert approved.status_code == 200
    assert len(client.get("/api/v1/faculty").json()) == 1


def test_registration_cannot_self_assign_privileged_role(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "self-admin@example.edu", "password": "secure-test-password-2026", "full_name": "Self Admin", "roles": ["admin"]},
    )
    assert response.status_code == 202
    assert response.json()["message"]


def test_application_document_rejects_mismatched_file_content(client):
    admin_headers = login(client, "admin@example.edu", "admin-test-password-2026")
    program = client.post(
        "/api/v1/admin/programs",
        headers=admin_headers,
        json={"name": "Upload Test Program", "level": "Undergraduate", "published": True},
    ).json()
    register(client)
    applicant_headers = login(client, "applicant@example.edu", "secure-test-password-2026")
    application = client.post("/api/v1/applications", headers=applicant_headers, json={"program_id": program["id"]}).json()
    response = client.post(
        f"/api/v1/applications/{application['id']}/documents",
        headers=applicant_headers,
        files={"file": ("malformed.png", b"not a png", "image/png")},
    )
    assert response.status_code == 415


def test_email_verification_is_required_and_one_time(client):
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "unverified@example.edu", "password": "secure-test-password-2026", "full_name": "Unverified Applicant"},
    )
    assert registration.status_code == 202
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "unverified@example.edu", "password": "secure-test-password-2026"},
    ).status_code == 403
    link = client.app.state.test_email_service.sent[-1]
    verified = client.post("/api/v1/auth/verify-email", json={"token": link["token"]})
    assert verified.status_code == 200
    assert client.post("/api/v1/auth/verify-email", json={"token": link["token"]}).status_code == 400
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "unverified@example.edu", "password": "secure-test-password-2026"},
    ).status_code == 200


def test_password_recovery_is_generic_one_time_and_revokes_existing_tokens(client):
    register(client)
    old_headers = login(client, "applicant@example.edu", "secure-test-password-2026")
    unknown = client.post("/api/v1/auth/password-reset/request", json={"email": "unknown@example.edu"})
    known = client.post("/api/v1/auth/password-reset/request", json={"email": "applicant@example.edu"})
    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    reset_link = client.app.state.test_email_service.sent[-1]
    changed = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_link["token"], "password": "changed-test-password-2026"},
    )
    assert changed.status_code == 200
    assert client.get("/api/v1/auth/me", headers=old_headers).status_code == 401
    assert client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_link["token"], "password": "another-test-password-2026"},
    ).status_code == 400
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "applicant@example.edu", "password": "secure-test-password-2026"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"email": "applicant@example.edu", "password": "changed-test-password-2026"},
    ).status_code == 200


def test_document_access_is_owner_or_admin_only(client, tmp_path, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "uploads_directory", str(tmp_path))

    admin_headers = login(client, "admin@example.edu", "admin-test-password-2026")
    program = client.post(
        "/api/v1/admin/programs",
        headers=admin_headers,
        json={"name": "Private Documents Program", "level": "Undergraduate", "published": True},
    ).json()
    register(client, "owner@example.edu")
    owner_headers = login(client, "owner@example.edu", "secure-test-password-2026")
    owner_app = client.post("/api/v1/applications", headers=owner_headers, json={"program_id": program["id"]}).json()
    upload = client.post(
        f"/api/v1/applications/{owner_app['id']}/documents",
        headers=owner_headers,
        files={"file": ("..\\private.png", b"\x89PNG\r\n\x1a\nsample-image-data", "image/png")},
    )
    assert upload.status_code == 201
    documents = client.get(f"/api/v1/applications/{owner_app['id']}/documents", headers=owner_headers).json()
    assert documents[0]["name"] == "private.png"
    owner_download = client.get(
        f"/api/v1/applications/{owner_app['id']}/documents/{documents[0]['id']}",
        headers=owner_headers,
    )
    assert owner_download.status_code == 200
    assert owner_download.headers["cache-control"] == "private, no-store"
    register(client, "other@example.edu")
    other_headers = login(client, "other@example.edu", "secure-test-password-2026")
    assert client.get(
        f"/api/v1/applications/{owner_app['id']}/documents",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/applications/{owner_app['id']}/documents/{documents[0]['id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/admin/documents/{documents[0]['id']}",
        headers=admin_headers,
    ).status_code == 200


def test_document_upload_enforces_size_limit_and_scanner(monkeypatch, client, tmp_path):
    from app.api import applications
    from app.core import config
    from app.core.file_scanner import MalwareDetected
    monkeypatch.setattr(config.settings, "uploads_directory", str(tmp_path))
    monkeypatch.setattr(config.settings, "max_upload_bytes", 16)
    admin_headers = login(client, "admin@example.edu", "admin-test-password-2026")
    program = client.post(
        "/api/v1/admin/programs",
        headers=admin_headers,
        json={"name": "Upload Restrictions", "level": "Undergraduate", "published": True},
    ).json()
    register(client)
    applicant_headers = login(client, "applicant@example.edu", "secure-test-password-2026")
    application = client.post("/api/v1/applications", headers=applicant_headers, json={"program_id": program["id"]}).json()
    too_large = client.post(
        f"/api/v1/applications/{application['id']}/documents",
        headers=applicant_headers,
        files={"file": ("large.png", b"\x89PNG\r\n\x1a\n" + b"x" * 20, "image/png")},
    )
    assert too_large.status_code == 413
    monkeypatch.setattr(config.settings, "max_upload_bytes", 100)
    monkeypatch.setattr(applications, "scan_document", lambda _: (_ for _ in ()).throw(MalwareDetected()))
    infected = client.post(
        f"/api/v1/applications/{application['id']}/documents",
        headers=applicant_headers,
        files={"file": ("infected.png", b"\x89PNG\r\n\x1a\nsafe-signature", "image/png")},
    )
    assert infected.status_code == 422
    assert list(Path(tmp_path).iterdir()) == []


def test_jwt_tampering_and_required_claims_are_rejected(client):
    register(client)
    headers = login(client, "applicant@example.edu", "secure-test-password-2026")
    token = headers["Authorization"].removeprefix("Bearer ")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}tampered"}).status_code == 401
    expired = jwt.encode(
        {
            "sub": "1",
            "ver": 0,
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iss": settings.app_name,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_expired_verification_token_is_rejected(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "expired@example.edu", "password": "secure-test-password-2026", "full_name": "Expired Link"},
    )
    token = client.app.state.test_email_service.sent[-1]["token"]
    with client.app.state.test_session() as db:
        db.execute(
            update(EmailAction)
            .where(EmailAction.token_hash == hash_action_token(token))
            .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        )
        db.commit()
    result = client.post("/api/v1/auth/verify-email", json={"token": token})
    assert result.status_code == 400


def test_request_size_limit_rejects_oversized_body(client, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "max_upload_bytes", 1_024)
    response = client.post(
        "/api/v1/contact",
        content=b"x" * 1_300_000,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


def test_admin_content_is_published_only_when_requested(client):
    admin_headers = login(client, "admin@example.edu", "admin-test-password-2026")
    unpublished = client.post(
        "/api/v1/admin/news",
        headers=admin_headers,
        json={"title": "Draft story", "slug": "draft-story", "body": "Draft copy", "published": False},
    )
    assert unpublished.status_code == 201
    assert client.get("/api/v1/news").json() == []

    published = client.post(
        "/api/v1/admin/notices",
        headers=admin_headers,
        json={"title": "Officially approved notice", "body": "Approved copy", "published": True},
    )
    assert published.status_code == 201
    assert client.get("/api/v1/notices").json()[0]["title"] == "Officially approved notice"
