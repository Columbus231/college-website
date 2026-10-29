from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Permission, Role

ROLE_PERMISSIONS = {
    "applicant": {"applications:create", "applications:read-own", "documents:upload-own"},
    "student": {"student:read-own"},
    "faculty": {"faculty:teach-assigned"},
    "admin": {"content:manage", "applications:review", "users:manage", "contacts:review", "audit:read", "faculty:approve"},
}


def configure_role_permissions(db: Session, role: Role) -> None:
    permissions: list[Permission] = []
    for name in ROLE_PERMISSIONS[role.name]:
        permission = db.scalar(select(Permission).where(Permission.name == name))
        if permission is None:
            permission = Permission(name=name, description=f"Allows {name.replace(':', ' ')}")
            db.add(permission)
        permissions.append(permission)
    role.permissions = permissions
