"""add connection_status to ms365_connections

Revision ID: a1b2c3d4e5f6
Revises: 3a44e84b2d48
Create Date: 2026-03-26 17:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '3a44e84b2d48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ms365_connections',
        sa.Column(
            'connection_status',
            sa.String(length=50),
            nullable=False,
            server_default='active',
            comment='Connection state: active, token_expired, needs_reauth',
        ),
    )
    # Widen folder column — MS Graph parentFolderId can exceed 100 chars
    op.alter_column(
        'synced_emails',
        'folder',
        type_=sa.String(length=255),
        existing_type=sa.String(length=100),
    )


def downgrade() -> None:
    op.drop_column('ms365_connections', 'connection_status')
