"""Merge heads

Revision ID: b3beb7dfdaf3
Revises: a1b2c3d4e5f6, rls_001
Create Date: 2026-03-09 22:41:24.968327

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3beb7dfdaf3'
down_revision: Union[str, Sequence[str], None] = ('a1b2c3d4e5f6', 'rls_001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
