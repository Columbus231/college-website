from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    programs: Mapped[list["AcademicProgram"]] = relationship(back_populates="department")


class AcademicProgram(Base):
    __tablename__ = "academic_programs"
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    level: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text, default="")
    eligibility: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[str] = mapped_column(String(80), default="")
    intake: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    department: Mapped[Department | None] = relationship(back_populates="programs")
    courses: Mapped[list["Course"]] = relationship(back_populates="program")


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("academic_programs.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    resource_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    program: Mapped[AcademicProgram] = relationship(back_populates="courses")


class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("academic_programs.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    statement: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    __table_args__ = (UniqueConstraint("applicant_id", "program_id", name="uq_applicant_program_application"),)


class ApplicationDocument(Base):
    __tablename__ = "application_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FacultyProfile(Base):
    __tablename__ = "faculty_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    designation: Mapped[str] = mapped_column(String(120), default="")
    qualifications: Mapped[str] = mapped_column(String(250), default="")
    research_interests: Mapped[str] = mapped_column(Text, default="")
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user: Mapped["User"] = relationship(back_populates="faculty_profile")


class StudentProfile(Base):
    __tablename__ = "student_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    student_number: Mapped[str] = mapped_column(String(64), unique=True)
    user: Mapped["User"] = relationship(back_populates="student_profile")


class NewsArticle(Base):
    __tablename__ = "news_articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), default="News")
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    venue: Mapped[str] = mapped_column(String(200), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Notice(Base):
    __tablename__ = "notices"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), default="General")
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContactSubmission(Base):
    __tablename__ = "contact_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), index=True)
    interest: Mapped[str] = mapped_column(String(160), default="")
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WebsiteSetting(Base):
    __tablename__ = "website_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(80))
    resource_id: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
