"""add admin announcements table

Revision ID: 7d8d8b1f9a0f
Revises: e3bf38fb2c7c
Create Date: 2025-11-07 19:55:44.457943

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7d8d8b1f9a0f"
down_revision: Union[str, Sequence[str], None] = "e3bf38fb2c7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("show_on_home", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("timezone('utc', now())")),
    )
    op.create_index("ix_admin_announcements_show", "admin_announcements", ["show_on_home", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_announcements_show", table_name="admin_announcements")
    op.drop_table("admin_announcements")
