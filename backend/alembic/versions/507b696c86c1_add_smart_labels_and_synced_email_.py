"""Add smart_labels and synced_email.smart_label

Revision ID: 507b696c86c1
Revises: c2d3e4f5g6h7
Create Date: 2026-03-14 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '507b696c86c1'
down_revision: Union[str, Sequence[str], None] = 'c2d3e4f5g6h7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('smart_labels',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False),
        sa.Column('tenant_id', sa.String(length=36), nullable=False, comment='Tenant identifier for multi-tenant isolation'),
        sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_smart_labels_tenant_id'), 'smart_labels', ['tenant_id'], unique=False)

    op.add_column('synced_emails', sa.Column('smart_label', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('synced_emails', 'smart_label')
    op.drop_index(op.f('ix_smart_labels_tenant_id'), table_name='smart_labels')
    op.drop_table('smart_labels')
