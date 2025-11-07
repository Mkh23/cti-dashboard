"""add cattle table and scan metrics

Revision ID: c844da55a7a7
Revises: 615f4fc9f620
Create Date: 2025-11-07 10:16:00.378292

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c844da55a7a7'
down_revision: Union[str, Sequence[str], None] = '615f4fc9f620'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cattle",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True, unique=True),
        sa.Column("born_date", sa.Date(), nullable=True),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("farms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("timezone('utc', now())")),
    )
    op.create_index("ix_cattle_farm_id", "cattle", ["farm_id"])

    op.add_column("scans", sa.Column("cattle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cattle.id", ondelete="SET NULL"), nullable=True))
    op.add_column("scans", sa.Column("imf", sa.Numeric(6, 4), nullable=True))
    op.add_column("scans", sa.Column("backfat_thickness", sa.Numeric(6, 3), nullable=True))
    op.add_column("scans", sa.Column("animal_weight", sa.Numeric(10, 2), nullable=True))
    op.add_column("scans", sa.Column("animal_rfid", sa.Text(), nullable=True))
    op.create_index("ix_scans_cattle_id", "scans", ["cattle_id"])
    op.create_index("ix_scans_animal_rfid", "scans", ["animal_rfid"])

    op.add_column("animals", sa.Column("rfid", sa.Text(), nullable=True))
    op.add_column(
        "animals",
        sa.Column(
            "cattle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cattle.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_animals_rfid", "animals", ["rfid"], unique=True)
    op.create_index("ix_animals_cattle_id", "animals", ["cattle_id"])


def downgrade() -> None:
    op.drop_index("ix_animals_cattle_id", table_name="animals")
    op.drop_index("ix_animals_rfid", table_name="animals")
    op.drop_column("animals", "cattle_id")
    op.drop_column("animals", "rfid")

    op.drop_index("ix_scans_animal_rfid", table_name="scans")
    op.drop_index("ix_scans_cattle_id", table_name="scans")
    op.drop_column("scans", "animal_rfid")
    op.drop_column("scans", "animal_weight")
    op.drop_column("scans", "backfat_thickness")
    op.drop_column("scans", "imf")
    op.drop_column("scans", "cattle_id")

    op.drop_index("ix_cattle_farm_id", table_name="cattle")
    op.drop_table("cattle")
