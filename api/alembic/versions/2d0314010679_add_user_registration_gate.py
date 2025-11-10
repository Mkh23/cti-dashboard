"""add user registration gate

Revision ID: 2d0314010679
Revises: 0b5f977c20d6
Create Date: 2025-11-09 22:33:03.106408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d0314010679'
down_revision: Union[str, Sequence[str], None] = '0b5f977c20d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    status_enum = sa.Enum("pending", "approved", "rejected", name="registrationstatus")
    bind = op.get_bind()
    status_enum.create(bind, checkfirst=True)

    op.add_column(
        "users",
        sa.Column(
            "registration_status",
            status_enum,
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "users",
        sa.Column("requested_role", sa.Text(), nullable=True),
    )

    op.execute("UPDATE users SET registration_status = 'approved'")
    op.alter_column("users", "registration_status", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "requested_role")
    op.drop_column("users", "registration_status")

    status_enum = sa.Enum("pending", "approved", "rejected", name="registrationstatus")
    bind = op.get_bind()
    status_enum.drop(bind, checkfirst=True)
