"""Add membrane_connections table.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-08 15:50:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'membrane_connections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('membrane_connection_id', sa.String(255), nullable=False, index=True),
        sa.Column('integration_key', sa.String(100), nullable=False, index=True),
        sa.Column('connection_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('last_email_sync', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_calendar_sync', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.Text, nullable=True),
        # TenantMixin
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        # AuditMixin
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
        # SoftDeleteMixin
        sa.Column('is_deleted', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', sa.String(100), nullable=True),
        sa.Column('deleted_reason', sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table('membrane_connections')
