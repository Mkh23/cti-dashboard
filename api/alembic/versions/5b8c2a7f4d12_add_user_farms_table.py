"""Add user_farms association table

Revision ID: 5b8c2a7f4d12
Revises: ef0584204901
Create Date: 2025-10-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5b8c2a7f4d12"
down_revision: Union[str, Sequence[str], None] = "ef0584204901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_farms association table."""
    op.create_table(
        "user_farms",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("farm_id", sa.UUID(), nullable=False),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["farm_id"], ["farms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "farm_id"),
    )
    op.create_index("ix_user_farms_user_id", "user_farms", ["user_id"], unique=False)
    op.create_index("ix_user_farms_farm_id", "user_farms", ["farm_id"], unique=False)

    # Remove server defaults now that existing rows are initialized
    op.alter_column("user_farms", "is_owner", server_default=None)
    op.alter_column("user_farms", "created_at", server_default=None)


def downgrade() -> None:
    """Drop user_farms association table."""
    op.drop_index("ix_user_farms_farm_id", table_name="user_farms")
    op.drop_index("ix_user_farms_user_id", table_name="user_farms")
    op.drop_table("user_farms")
