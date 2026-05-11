"""add integration_settings table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-08 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'integration_settings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('integration_key', sa.String(length=100), nullable=False),
        sa.Column('scope_mode', sa.String(length=20), nullable=False, server_default='per-user'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('display_name', sa.String(length=200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tenant_id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'integration_key', name='uix_integration_setting_tenant_key'),
    )
    op.create_index(op.f('ix_integration_settings_integration_key'), 'integration_settings', ['integration_key'], unique=False)
    op.create_index(op.f('ix_integration_settings_tenant_id'), 'integration_settings', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_integration_settings_tenant_id'), table_name='integration_settings')
    op.drop_index(op.f('ix_integration_settings_integration_key'), table_name='integration_settings')
    op.drop_table('integration_settings')
