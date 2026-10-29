from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import DbSession, require_permissions
from app.core.roles import configure_role_permissions
from app.models import AcademicProgram, ApplicationDocument, AuditLog, Event, NewsArticle, Notice, User
from app.models import ApplicantProfile, FacultyProfile, Role, StudentProfile
from app.schemas import EventCreate, EventRead, NewsCreate, NewsRead, NoticeCreate, NoticeRead, ProgramCreate, ProgramRead, UserRoleUpdate
from app.schemas import ApplicationRead, ApplicationStatusUpdate, DepartmentCreate

router = APIRouter(prefix="/admin", tags=["administration"])


@router.post("/departments", status_code=status.HTTP_201_CREATED)
def create_department(body: DepartmentCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    from app.models import Department
    department = Department(name=body.name, description=body.description.strip())
    db.add(department)
    try:
        db.flush()
        db.add(AuditLog(actor_id=admin.id, action="department.create", resource_type="department", resource_id=str(department.id)))
        db.commit()
        db.refresh(department)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with this name already exists") from None
    return {"id": department.id, "name": department.name, "description": department.description}


@router.post("/programs", response_model=ProgramRead, status_code=status.HTTP_201_CREATED)
def create_program(body: ProgramCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    if body.department_id is not None and db.get(Department, body.department_id) is None:
        raise HTTPException(status_code=404, detail="Department not found")
    program = AcademicProgram(**body.model_dump())
    db.add(program)
    db.flush()
    db.add(AuditLog(actor_id=admin.id, action="program.create", resource_type="program", resource_id=str(program.id)))
    db.commit()
    db.refresh(program)
    return program


@router.patch("/programs/{program_id}", response_model=ProgramRead)
def update_program(program_id: int, body: ProgramCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    program = db.get(AcademicProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    if body.department_id is not None and db.get(Department, body.department_id) is None:
        raise HTTPException(status_code=404, detail="Department not found")
    for key, value in body.model_dump().items():
        setattr(program, key, value)
    db.add(AuditLog(actor_id=admin.id, action="program.update", resource_type="program", resource_id=str(program_id)))
    db.commit()
    db.refresh(program)
    return program


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(program_id: int, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    program = db.get(AcademicProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="Program not found")
    db.add(AuditLog(actor_id=admin.id, action="program.archive", resource_type="program", resource_id=str(program_id)))
    program.published = False
    db.commit()


@router.post("/news", response_model=NewsRead, status_code=status.HTTP_201_CREATED)
def create_news(body: NewsCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    article = NewsArticle(**body.model_dump(), published_at=datetime.now(timezone.utc) if body.published else None)
    db.add(article)
    db.add(AuditLog(actor_id=admin.id, action="news.create", resource_type="news", resource_id=body.slug))
    try:
        db.commit()
        db.refresh(article)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A news article with this slug already exists") from None
    return article


@router.post("/events", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(body: EventCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    event = Event(**body.model_dump())
    db.add(event)
    db.add(AuditLog(actor_id=admin.id, action="event.create", resource_type="event", resource_id=body.title))
    db.commit()
    db.refresh(event)
    return event


@router.post("/notices", response_model=NoticeRead, status_code=status.HTTP_201_CREATED)
def create_notice(body: NoticeCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    notice = Notice(**body.model_dump())
    db.add(notice)
    db.add(AuditLog(actor_id=admin.id, action="notice.create", resource_type="notice", resource_id=body.title))
    db.commit()
    db.refresh(notice)
    return notice


@router.get("/applications", response_model=list[ApplicationRead])
def list_applications(db: DbSession, admin: Annotated[User, Depends(require_permissions("applications:review"))], offset: int = 0, limit: int = 50):
    from app.models import Application
    return db.scalars(select(Application).order_by(Application.created_at.desc()).offset(offset).limit(min(limit, 100))).all()


@router.get("/documents/{document_id}")
def download_application_document(
    document_id: int,
    db: DbSession,
    admin: Annotated[User, Depends(require_permissions("applications:review"))],
):
    document = db.get(ApplicationDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    from app.api.applications import _document_response
    return _document_response(document)


@router.patch("/news/{article_id}", response_model=NewsRead)
def update_news(article_id: int, body: NewsCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    article = db.get(NewsArticle, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="News article not found")
    for key, value in body.model_dump().items():
        setattr(article, key, value)
    article.published_at = datetime.now(timezone.utc) if body.published and article.published_at is None else article.published_at
    db.add(AuditLog(actor_id=admin.id, action="news.update", resource_type="news", resource_id=str(article_id)))
    try:
        db.commit()
        db.refresh(article)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A news article with this slug already exists") from None
    return article


@router.patch("/events/{event_id}", response_model=EventRead)
def update_event(event_id: int, body: EventCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    for key, value in body.model_dump().items():
        setattr(event, key, value)
    db.add(AuditLog(actor_id=admin.id, action="event.update", resource_type="event", resource_id=str(event_id)))
    db.commit()
    db.refresh(event)
    return event


@router.patch("/notices/{notice_id}", response_model=NoticeRead)
def update_notice(notice_id: int, body: NoticeCreate, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    notice = db.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="Notice not found")
    for key, value in body.model_dump().items():
        setattr(notice, key, value)
    db.add(AuditLog(actor_id=admin.id, action="notice.update", resource_type="notice", resource_id=str(notice_id)))
    db.commit()
    db.refresh(notice)
    return notice


@router.delete("/news/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_news(article_id: int, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    article = db.get(NewsArticle, article_id)
    if article is None:
        raise HTTPException(status_code=404, detail="News article not found")
    db.add(AuditLog(actor_id=admin.id, action="news.delete", resource_type="news", resource_id=str(article_id)))
    db.delete(article)
    db.commit()


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    db.add(AuditLog(actor_id=admin.id, action="event.delete", resource_type="event", resource_id=str(event_id)))
    db.delete(event)
    db.commit()


@router.delete("/notices/{notice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notice(notice_id: int, db: DbSession, admin: Annotated[User, Depends(require_permissions("content:manage"))]):
    notice = db.get(Notice, notice_id)
    if notice is None:
        raise HTTPException(status_code=404, detail="Notice not found")
    db.add(AuditLog(actor_id=admin.id, action="notice.delete", resource_type="notice", resource_id=str(notice_id)))
    db.delete(notice)
    db.commit()


@router.patch("/applications/{application_id}/status", response_model=ApplicationRead)
def set_application_status(application_id: int, body: ApplicationStatusUpdate, db: DbSession, admin: Annotated[User, Depends(require_permissions("applications:review"))]):
    from app.models import Application
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    application.status = body.status
    db.add(AuditLog(actor_id=admin.id, action="application.status.update", resource_type="application", resource_id=str(application_id)))
    db.commit()
    db.refresh(application)
    return application


@router.get("/contact-submissions")
def list_contact_submissions(db: DbSession, admin: Annotated[User, Depends(require_permissions("contacts:review"))], offset: int = 0, limit: int = 50):
    from app.models import ContactSubmission
    submissions = db.scalars(select(ContactSubmission).order_by(ContactSubmission.created_at.desc()).offset(offset).limit(min(limit, 100))).all()
    return [{"id": item.id, "name": item.name, "email": item.email, "interest": item.interest, "message": item.message, "created_at": item.created_at, "reviewed": item.reviewed} for item in submissions]


@router.get("/audit-logs")
def list_audit_logs(db: DbSession, admin: Annotated[User, Depends(require_permissions("audit:read"))], offset: int = 0, limit: int = 50):
    from app.models import AuditLog
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(min(limit, 100))).all()
    return [{"id": item.id, "actor_id": item.actor_id, "action": item.action, "resource_type": item.resource_type, "resource_id": item.resource_id, "created_at": item.created_at} for item in logs]


@router.get("/users")
def list_users(db: DbSession, admin: Annotated[User, Depends(require_permissions("users:manage"))], offset: int = 0, limit: int = 50):
    users = db.scalars(select(User).order_by(User.created_at.desc()).offset(offset).limit(min(limit, 100))).all()
    return [{"id": item.id, "email": item.email, "full_name": item.full_name, "is_active": item.is_active, "roles": [role.name for role in item.roles]} for item in users]


@router.get("/faculty")
def list_faculty_profiles(db: DbSession, admin: Annotated[User, Depends(require_permissions("faculty:approve"))], offset: int = 0, limit: int = 50):
    profiles = db.scalars(select(FacultyProfile).order_by(FacultyProfile.id).offset(offset).limit(min(limit, 100))).all()
    return [{"id": profile.id, "user_id": profile.user_id, "name": profile.user.full_name, "designation": profile.designation, "qualifications": profile.qualifications, "approved": profile.approved} for profile in profiles]


@router.patch("/faculty/{profile_id}/approve")
def approve_faculty_profile(profile_id: int, db: DbSession, admin: Annotated[User, Depends(require_permissions("faculty:approve"))]):
    profile = db.get(FacultyProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Faculty profile not found")
    profile.approved = True
    db.add(AuditLog(actor_id=admin.id, action="faculty.approve", resource_type="faculty_profile", resource_id=str(profile_id)))
    db.commit()
    return {"id": profile.id, "approved": profile.approved}


@router.patch("/users/{user_id}/role")
def update_user_role(user_id: int, body: UserRoleUpdate, db: DbSession, admin: Annotated[User, Depends(require_permissions("users:manage"))]):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if any(role.name == "admin" for role in user.roles):
        raise HTTPException(status_code=409, detail="Administrator roles can only be provisioned through the operator setup command")
    if body.role == "student" and not body.student_number:
        raise HTTPException(status_code=422, detail="A verified student number is required")
    role = db.scalar(select(Role).where(Role.name == body.role))
    if role is None:
        role = Role(name=body.role)
        db.add(role)
        db.flush()
    configure_role_permissions(db, role)
    user.roles = [role]
    if body.role == "student":
        if user.student_profile is None:
            user.student_profile = StudentProfile(student_number=body.student_number or "")
        else:
            user.student_profile.student_number = body.student_number or user.student_profile.student_number
        if user.applicant_profile is not None:
            db.delete(user.applicant_profile)
        if user.faculty_profile is not None:
            db.delete(user.faculty_profile)
    elif body.role == "faculty":
        if user.faculty_profile is None:
            user.faculty_profile = FacultyProfile(designation=body.designation, qualifications=body.qualifications, approved=False)
        else:
            user.faculty_profile.designation = body.designation
            user.faculty_profile.qualifications = body.qualifications
            user.faculty_profile.approved = False
        if user.applicant_profile is not None:
            db.delete(user.applicant_profile)
        if user.student_profile is not None:
            db.delete(user.student_profile)
    else:
        if user.applicant_profile is None:
            user.applicant_profile = ApplicantProfile()
        if user.student_profile is not None:
            db.delete(user.student_profile)
        if user.faculty_profile is not None:
            db.delete(user.faculty_profile)
    db.add(AuditLog(actor_id=admin.id, action="user.role.update", resource_type="user", resource_id=str(user_id)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That student number is already assigned") from None
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "is_active": user.is_active, "roles": [item.name for item in user.roles]}


@router.patch("/contact-submissions/{submission_id}/review")
def review_contact_submission(submission_id: int, db: DbSession, admin: Annotated[User, Depends(require_permissions("contacts:review"))]):
    from app.models import ContactSubmission
    submission = db.get(ContactSubmission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Contact submission not found")
    submission.reviewed = True
    db.add(AuditLog(actor_id=admin.id, action="contact.review", resource_type="contact_submission", resource_id=str(submission_id)))
    db.commit()
    return {"id": submission.id, "reviewed": submission.reviewed}
