import os
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.db import SessionLocal
from app.models import AcademicProgram, Department, NewsArticle, Notice


def main() -> None:
    if settings.environment != "development" or os.getenv("LOAD_DEMO_DATA") != "true":
        raise SystemExit("Demo data requires ENVIRONMENT=development and LOAD_DEMO_DATA=true.")
    with SessionLocal() as db:
        department = db.scalar(select(Department).where(Department.name == "Sample School of Computing"))
        if department is None:
            department = Department(
                name="Sample School of Computing",
                description="Fictional development data; replace with approved college information.",
            )
            db.add(department)
            db.flush()
        program = db.scalar(select(AcademicProgram).where(AcademicProgram.name == "Sample Computer Science"))
        if program is None:
            db.add(AcademicProgram(
                department_id=department.id,
                name="Sample Computer Science",
                level="Undergraduate",
                description="Fictional demo content for local development only.",
                eligibility="Sample eligibility; not official.",
                duration="Sample duration; not official.",
                published=True,
            ))
        news = db.scalar(select(NewsArticle).where(NewsArticle.slug == "sample-campus-update"))
        if news is None:
            db.add(NewsArticle(
                title="Sample campus update",
                slug="sample-campus-update",
                category="Development sample",
                body="Fictional development content. Do not publish without institutional approval.",
                published=True,
                published_at=datetime.now(timezone.utc),
            ))
        notice = db.scalar(select(Notice).where(Notice.title == "Sample development notice"))
        if notice is None:
            db.add(Notice(
                title="Sample development notice",
                category="Development sample",
                body="Fictional sample data for local development only.",
                published=True,
            ))
        db.commit()
    print("Fictional development program, news, and notice seeded.")


if __name__ == "__main__":
    main()
