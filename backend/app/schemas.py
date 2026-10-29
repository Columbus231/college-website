from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Full name must contain at least two non-space characters")
        return normalized


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    roles: list[str]
    model_config = ConfigDict(from_attributes=True)


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageRead(BaseModel):
    message: str


class EmailTokenRequest(BaseModel):
    email: EmailStr


class ActionTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class PasswordResetRequest(ActionTokenRequest):
    password: str = Field(min_length=12, max_length=128)


class ProgramCreate(BaseModel):
    department_id: int | None = None
    name: str = Field(min_length=2, max_length=160)
    level: str = Field(min_length=2, max_length=40)
    description: str = Field(default="", max_length=10_000)
    eligibility: str = Field(default="", max_length=5_000)
    duration: str = Field(default="", max_length=80)
    intake: int | None = Field(default=None, ge=0, le=100_000)
    published: bool = False

    @field_validator("name", "level")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Value must contain at least two non-space characters")
        return normalized


class ProgramRead(ProgramCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NewsCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=220)
    body: str = Field(min_length=1, max_length=50_000)
    category: str = Field(default="News", max_length=60)
    published: bool = False


class NewsRead(NewsCreate):
    id: int
    published_at: datetime | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=10_000)
    venue: str = Field(default="", max_length=200)
    starts_at: datetime
    expires_at: datetime | None = None
    published: bool = False

    @model_validator(mode="after")
    def expires_after_start(self):
        if self.expires_at is not None and self.expires_at <= self.starts_at:
            raise ValueError("Event expiry must be after its start time")
        return self


class EventRead(EventCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class NoticeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=1, max_length=10_000)
    category: str = Field(default="General", max_length=60)
    published: bool = False
    expires_at: datetime | None = None


class NoticeRead(NoticeCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ContactCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    interest: str = Field(default="", max_length=160)
    message: str = Field(min_length=4, max_length=2_000)

    @field_validator("name", "message")
    @classmethod
    def normalize_contact_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field must not be blank")
        return normalized


class ApplicationCreate(BaseModel):
    program_id: int
    statement: str = Field(default="", max_length=5_000)


class ApplicationRead(BaseModel):
    id: int
    reference: str
    program_id: int
    status: str
    statement: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ApplicationStatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(draft|submitted|under_review|accepted|rejected|withdrawn)$")


class UserRoleUpdate(BaseModel):
    role: Literal["applicant", "student", "faculty"]
    student_number: str | None = Field(default=None, min_length=2, max_length=64)
    designation: str = Field(default="", max_length=120)
    qualifications: str = Field(default="", max_length=250)


class FacultyRead(BaseModel):
    id: int
    name: str
    designation: str
    qualifications: str
    research_interests: str


class DepartmentRead(BaseModel):
    id: int
    name: str
    description: str
    model_config = ConfigDict(from_attributes=True)


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=5_000)

    @field_validator("name")
    @classmethod
    def normalize_department_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Department name must contain at least two non-space characters")
        return normalized
