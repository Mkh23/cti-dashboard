"""repair legacy cattle schema to include groups columns

Revision ID: 4f8c9c2a2b7d
Revises: 3c2d4f7a9b10
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "4f8c9c2a2b7d"
down_revision: Union[str, Sequence[str], None] = "3c2d4f7a9b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create groups table if missing (legacy cattle schema)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS groups (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            external_id TEXT UNIQUE,
            born_date DATE,
            farm_id UUID REFERENCES farms(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT timezone('utc', now()),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT timezone('utc', now())
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_groups_farm_id ON groups (farm_id);")

    # Add group_id columns if missing
    op.execute("ALTER TABLE scans ADD COLUMN IF NOT EXISTS group_id UUID;")
    op.execute("ALTER TABLE animals ADD COLUMN IF NOT EXISTS group_id UUID;")

    # Add foreign keys if missing
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'scans_group_id_fkey'
            ) THEN
                ALTER TABLE scans
                ADD CONSTRAINT scans_group_id_fkey
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'animals_group_id_fkey'
            ) THEN
                ALTER TABLE animals
                ADD CONSTRAINT animals_group_id_fkey
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_scans_group_id ON scans (group_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_animals_group_id ON animals (group_id);")


def downgrade() -> None:
    # Non-destructive: leave legacy repair in place.
    pass
