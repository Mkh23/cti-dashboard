"""add backfat line mask asset to scans

Revision ID: 3c2d4f7a9b10
Revises: 2d0314010679
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c2d4f7a9b10"
down_revision: Union[str, Sequence[str], None] = "2d0314010679"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("backfat_line_asset_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_scans_backfat_line_asset_id_assets",
        "scans",
        "assets",
        ["backfat_line_asset_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_scans_backfat_line_asset_id_assets", "scans", type_="foreignkey")
    op.drop_column("scans", "backfat_line_asset_id")
