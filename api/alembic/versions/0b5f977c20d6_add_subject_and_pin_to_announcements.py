"""add subject and pin priority to admin announcements

Revision ID: 0b5f977c20d6
Revises: 7d8d8b1f9a0f
Create Date: 2025-11-09 23:59:29.862233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0b5f977c20d6"
down_revision: Union[str, Sequence[str], None] = "7d8d8b1f9a0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("admin_announcements", sa.Column("subject", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "admin_announcements",
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("admin_announcements", "subject", server_default=None)
    op.create_index(
        "ix_admin_announcements_pinned_created",
        "admin_announcements",
        ["pinned", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_announcements_pinned_created", table_name="admin_announcements")
    op.drop_column("admin_announcements", "pinned")
    op.drop_column("admin_announcements", "subject")
