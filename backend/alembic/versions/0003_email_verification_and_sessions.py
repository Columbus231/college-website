"""Add verified email, token revocation, and one-time account actions."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003_email_actions"
down_revision = "0002_role_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if "email_verified" not in {column["name"] for column in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    if "token_version" not in {column["name"] for column in inspector.get_columns("users")}:
        op.add_column("users", sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))
    if not inspector.has_table("email_actions"):
        op.create_table(
            "email_actions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("purpose", sa.String(length=32), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_email_actions_user_id", "email_actions", ["user_id"])
        op.create_index("ix_email_actions_purpose", "email_actions", ["purpose"])
        op.create_index("ix_email_actions_token_hash", "email_actions", ["token_hash"])
        op.create_index("ix_email_actions_expires_at", "email_actions", ["expires_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if inspect(bind).has_table("email_actions"):
        op.drop_table("email_actions")
    columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "token_version" in columns:
        op.drop_column("users", "token_version")
    if "email_verified" in columns:
        op.drop_column("users", "email_verified")
