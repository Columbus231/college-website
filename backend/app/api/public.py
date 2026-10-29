from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.rate_limit import limiter
from app.models import AcademicProgram, ContactSubmission, Event, NewsArticle, Notice
from app.models import Department, FacultyProfile, User
from app.schemas import ContactCreate, DepartmentRead, EventRead, FacultyRead, NewsRead, NoticeRead, ProgramRead

router = APIRouter(tags=["public"])


@router.get("/programs", response_model=list[ProgramRead])
def programs(db: DbSession, offset: int = 0, limit: int = 50):
    return db.scalars(select(AcademicProgram).where(AcademicProgram.published.is_(True)).order_by(AcademicProgram.name).offset(offset).limit(min(limit, 100))).all()


@router.get("/departments", response_model=list[DepartmentRead])
def departments(db: DbSession, offset: int = 0, limit: int = 50):
    return db.scalars(select(Department).order_by(Department.name).offset(offset).limit(min(limit, 100))).all()


@router.get("/faculty", response_model=list[FacultyRead])
def faculty(db: DbSession, offset: int = 0, limit: int = 50):
    profiles = db.scalars(
        select(FacultyProfile)
        .join(User, User.id == FacultyProfile.user_id)
        .where(FacultyProfile.approved.is_(True), User.is_active.is_(True))
        .order_by(User.full_name)
        .offset(offset)
        .limit(min(limit, 100))
    ).all()
    return [
        {
            "id": profile.id,
            "name": profile.user.full_name,
            "designation": profile.designation,
            "qualifications": profile.qualifications,
            "research_interests": profile.research_interests,
        }
        for profile in profiles
    ]


@router.get("/news", response_model=list[NewsRead])
def news(db: DbSession, offset: int = 0, limit: int = 20):
    return db.scalars(select(NewsArticle).where(NewsArticle.published.is_(True)).order_by(NewsArticle.published_at.desc().nullslast()).offset(offset).limit(min(limit, 100))).all()


@router.get("/events", response_model=list[EventRead])
def events(db: DbSession, offset: int = 0, limit: int = 20):
    now = datetime.now(timezone.utc)
    query = select(Event).where(Event.published.is_(True), Event.starts_at >= now).order_by(Event.starts_at).offset(offset).limit(min(limit, 100))
    return db.scalars(query).all()


@router.get("/notices", response_model=list[NoticeRead])
def notices(db: DbSession, offset: int = 0, limit: int = 20):
    now = datetime.now(timezone.utc)
    query = select(Notice).where(Notice.published.is_(True)).where((Notice.expires_at.is_(None)) | (Notice.expires_at >= now)).order_by(Notice.created_at.desc()).offset(offset).limit(min(limit, 100))
    return db.scalars(query).all()


@router.post("/contact", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def contact(request: Request, body: ContactCreate, db: DbSession) -> dict[str, str]:
    submission = ContactSubmission(name=body.name.strip(), email=body.email.lower(), interest=body.interest.strip(), message=body.message.strip())
    db.add(submission)
    db.commit()
    return {"message": "Your inquiry was received"}
