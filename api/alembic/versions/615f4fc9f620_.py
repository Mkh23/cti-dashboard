"""empty message

Revision ID: 615f4fc9f620
Revises: 0a1c4b9be2cf, 5b8c2a7f4d12
Create Date: 2025-11-06 09:52:28.784019

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '615f4fc9f620'
down_revision: Union[str, Sequence[str], None] = ('0a1c4b9be2cf', '5b8c2a7f4d12')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
