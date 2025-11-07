"""add ribeye area, clarity/usability, and label to scans

Revision ID: e3bf38fb2c7c
Revises: c844da55a7a7
Create Date: 2025-11-07 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3bf38fb2c7c"
down_revision: Union[str, Sequence[str], None] = "c844da55a7a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


quality_enum = sa.Enum("good", "medium", "bad", name="scan_clarity_enum")
usability_enum = sa.Enum("good", "medium", "bad", name="scan_usability_enum")


def upgrade() -> None:
    bind = op.get_bind()
    quality_enum.create(bind, checkfirst=True)
    usability_enum.create(bind, checkfirst=True)

    op.add_column("scans", sa.Column("ribeye_area", sa.Numeric(8, 2), nullable=True))
    op.add_column("scans", sa.Column("clarity", quality_enum, nullable=True))
    op.add_column("scans", sa.Column("usability", usability_enum, nullable=True))
    op.add_column("scans", sa.Column("label", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scans", "label")
    op.drop_column("scans", "usability")
    op.drop_column("scans", "clarity")
    op.drop_column("scans", "ribeye_area")

    bind = op.get_bind()
    usability_enum.drop(bind, checkfirst=True)
    quality_enum.drop(bind, checkfirst=True)
