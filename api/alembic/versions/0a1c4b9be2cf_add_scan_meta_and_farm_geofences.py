"""add scan meta/grading fields and farm geofences table"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0a1c4b9be2cf"
# down_revision = "ef0584204901_add_phone_number_and_address_to_users"
down_revision = "ef0584204901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("grading", sa.Text(), nullable=True))
    op.add_column("scans", sa.Column("meta", postgresql.JSONB(), nullable=True))

    op.create_table(
        "farm_geofences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("farm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("farms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("geometry", Geometry(geometry_type="POLYGON", srid=4326, spatial_index=False), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("timezone('utc', now())")),
    )
    op.create_index("ix_farm_geofences_farm_id", "farm_geofences", ["farm_id"])
    op.create_index(
        "idx_farm_geofences_geom_gist",
        "farm_geofences",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_farm_geofences_farm_id", table_name="farm_geofences")
    op.drop_index("idx_farm_geofences_geom_gist", table_name="farm_geofences")
    op.drop_table("farm_geofences")

    op.drop_column("scans", "meta")
    op.drop_column("scans", "grading")
