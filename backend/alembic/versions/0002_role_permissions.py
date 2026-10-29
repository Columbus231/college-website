"""Add role-to-permission assignments."""
from alembic import op

from app.models.user import role_permissions
from app.db import Base
from app.models import Permission

revision = "0002_role_permissions"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Permission.__table__, role_permissions])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[role_permissions, Permission.__table__])
