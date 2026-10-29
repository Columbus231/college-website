from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.core.roles import configure_role_permissions
from app.db import SessionLocal
from app.models import Role, User


def main() -> None:
    email_input = str(settings.admin_email) if settings.admin_email else input("Administrator email: ").strip()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(email_input)).lower()
    except ValidationError:
        raise SystemExit("Enter a valid administrator email address.") from None
    password = settings.admin_password or getpass("Administrator password (16+ characters): ")
    if len(password) < 16:
        raise SystemExit("ADMIN_PASSWORD must contain at least 16 characters.")
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("That account already exists; administrator provisioning did not change it.")
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        if admin_role is None:
            admin_role = Role(name="admin")
            db.add(admin_role)
            db.flush()
        configure_role_permissions(db, admin_role)
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name="College Administrator",
            email_verified=True,
            roles=[admin_role],
        )
        db.add(user)
        db.commit()
    print("Administrator account created.")


if __name__ == "__main__":
    main()
