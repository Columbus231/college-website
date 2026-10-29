import secrets
import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import DbSession, require_permissions, require_roles
from app.core.config import settings
from app.core.file_scanner import MalwareDetected, ScannerUnavailable, scan_document
from app.models import AcademicProgram, Application, ApplicationDocument, AuditLog, User
from app.schemas import ApplicationCreate, ApplicationRead, ApplicationStatusUpdate

router = APIRouter(prefix="/applications", tags=["applications"])
logger = logging.getLogger(__name__)
allowed_signatures = {
    ".pdf": (b"%PDF-", "application/pdf"),
    ".png": (b"\x89PNG\r\n\x1a\n", "image/png"),
    ".jpg": (b"\xff\xd8\xff", "image/jpeg"),
    ".jpeg": (b"\xff\xd8\xff", "image/jpeg"),
}


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_application(body: ApplicationCreate, db: DbSession, user: Annotated[User, Depends(require_roles("applicant"))]) -> Application:
    if db.scalar(select(AcademicProgram.id).where(AcademicProgram.id == body.program_id, AcademicProgram.published.is_(True))) is None:
        raise HTTPException(status_code=404, detail="Program not found")
    application = Application(
        reference=f"APP-{secrets.token_hex(6).upper()}",
        applicant_id=user.id,
        program_id=body.program_id,
        statement=body.statement.strip(),
        status="draft",
    )
    db.add(application)
    try:
        db.commit()
        db.refresh(application)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An application for this program already exists") from None
    return application


@router.post("/{application_id}/submit", response_model=ApplicationRead)
def submit_application(application_id: int, db: DbSession, user: Annotated[User, Depends(require_roles("applicant"))]) -> Application:
    application = db.scalar(select(Application).where(Application.id == application_id, Application.applicant_id == user.id))
    if application is None or application.status != "draft":
        raise HTTPException(status_code=404, detail="Draft application not found")
    application.status = "submitted"
    db.commit()
    db.refresh(application)
    return application


@router.get("/mine", response_model=list[ApplicationRead])
def my_applications(db: DbSession, user: Annotated[User, Depends(require_roles("applicant", "student"))]):
    return db.scalars(select(Application).where(Application.applicant_id == user.id).order_by(Application.created_at.desc())).all()


@router.post("/{application_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    application_id: int,
    db: DbSession,
    user: Annotated[User, Depends(require_roles("applicant"))],
    file: Annotated[UploadFile, File()],
) -> dict[str, str]:
    application = db.scalar(select(Application).where(Application.id == application_id, Application.applicant_id == user.id))
    if application is None or application.status != "draft":
        raise HTTPException(status_code=404, detail="Draft application not found")
    extension = Path(file.filename or "").suffix.lower()
    expected = allowed_signatures.get(extension)
    if expected is None or file.content_type != expected[1]:
        raise HTTPException(status_code=415, detail="Only PDF, PNG, and JPEG documents are accepted")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Document exceeds the upload size limit")
    if not content.startswith(expected[0]):
        raise HTTPException(status_code=415, detail="Document content does not match its file type")
    try:
        scan_document(content)
    except MalwareDetected:
        raise HTTPException(status_code=422, detail="Uploaded document failed malware scanning") from None
    except ScannerUnavailable:
        logger.error("Application document upload blocked because malware scanner is unavailable")
        raise HTTPException(status_code=503, detail="Document scanning is temporarily unavailable") from None
    upload_root = Path(settings.uploads_directory).resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    storage_key = secrets.token_hex(16) + extension
    destination = upload_root / storage_key
    safe_name = (file.filename or "document").replace("\\", "/").rsplit("/", 1)[-1]
    safe_name = "".join(character for character in safe_name if character.isprintable())[:255] or "document"
    try:
        with destination.open("xb") as stored:
            stored.write(content)
        db.add(ApplicationDocument(application_id=application.id, storage_key=storage_key, original_name=safe_name, media_type=expected[1], size_bytes=len(content)))
        db.commit()
    except OSError:
        destination.unlink(missing_ok=True)
        logger.exception("Application document could not be stored")
        raise HTTPException(status_code=503, detail="Document storage is temporarily unavailable") from None
    except SQLAlchemyError:
        destination.unlink(missing_ok=True)
        db.rollback()
        raise
    return {"message": "Document uploaded"}


def _document_response(document: ApplicationDocument) -> FileResponse:
    root = Path(settings.uploads_directory).resolve()
    target = (root / document.storage_key).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        target,
        media_type="application/octet-stream",
        filename=document.original_name,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.get("/{application_id}/documents")
def list_my_documents(
    application_id: int,
    db: DbSession,
    user: Annotated[User, Depends(require_roles("applicant", "student"))],
) -> list[dict[str, int | str]]:
    application = db.scalar(select(Application).where(Application.id == application_id, Application.applicant_id == user.id))
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    documents = db.scalars(
        select(ApplicationDocument)
        .where(ApplicationDocument.application_id == application.id)
        .order_by(ApplicationDocument.uploaded_at)
    ).all()
    return [{"id": item.id, "name": item.original_name, "size_bytes": item.size_bytes} for item in documents]


@router.get("/{application_id}/documents/{document_id}")
def download_my_document(
    application_id: int,
    document_id: int,
    db: DbSession,
    user: Annotated[User, Depends(require_roles("applicant", "student"))],
) -> FileResponse:
    document = db.scalar(
        select(ApplicationDocument)
        .join(Application, Application.id == ApplicationDocument.application_id)
        .where(
            ApplicationDocument.id == document_id,
            Application.id == application_id,
            Application.applicant_id == user.id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return _document_response(document)


@router.patch("/{application_id}/status", response_model=ApplicationRead)
def update_application_status(
    application_id: int,
    body: ApplicationStatusUpdate,
    db: DbSession,
    admin: Annotated[User, Depends(require_permissions("applications:review"))],
) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    application.status = body.status
    db.add(AuditLog(actor_id=admin.id, action="application.status.update", resource_type="application", resource_id=str(application_id)))
    db.commit()
    db.refresh(application)
    return application
