"""Add Membrane-backed tables: connections, synced emails, synced events.

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
    # ── membrane_connections ────────────────────────────────────
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

    # ── membrane_synced_emails ────────────────────────────────────
    op.create_table(
        'membrane_synced_emails',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('membrane_connection_id', sa.String(36),
                  sa.ForeignKey('membrane_connections.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('provider_message_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('provider', sa.String(50), nullable=False, server_default='microsoft-outlook'),
        sa.Column('subject', sa.String(500), nullable=True, index=True),
        sa.Column('body_preview', sa.Text, nullable=True),
        sa.Column('body_html', sa.Text, nullable=True),
        sa.Column('from_address', sa.String(255), nullable=True, index=True),
        sa.Column('from_name', sa.String(255), nullable=True),
        sa.Column('to_addresses', sa.JSON, nullable=True),
        sa.Column('cc_addresses', sa.JSON, nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('is_read', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('importance', sa.String(20), nullable=True, server_default='normal'),
        sa.Column('has_attachments', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('attachments_meta', sa.JSON, nullable=True),
        sa.Column('folder', sa.String(255), nullable=True, server_default='inbox', index=True),
        sa.Column('conversation_id', sa.String(255), nullable=True, index=True),
        sa.Column('linked_contact_id', sa.String(36), nullable=True, index=True),
        sa.Column('linked_organization_id', sa.String(36), nullable=True, index=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
    )

    # ── membrane_synced_events ────────────────────────────────────
    op.create_table(
        'membrane_synced_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('membrane_connection_id', sa.String(36),
                  sa.ForeignKey('membrane_connections.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('user_id', sa.String(36), nullable=False, index=True),
        sa.Column('provider_event_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('provider', sa.String(50), nullable=False, server_default='microsoft-outlook'),
        sa.Column('subject', sa.String(500), nullable=True, index=True),
        sa.Column('body_html', sa.Text, nullable=True),
        sa.Column('location', sa.String(500), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_all_day', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('organizer_email', sa.String(255), nullable=True, index=True),
        sa.Column('organizer_name', sa.String(255), nullable=True),
        sa.Column('attendees', sa.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=True, server_default='none'),
        sa.Column('is_cancelled', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('recurrence', sa.JSON, nullable=True),
        sa.Column('online_meeting_url', sa.Text, nullable=True),
        sa.Column('linked_contact_id', sa.String(36), nullable=True, index=True),
        sa.Column('linked_organization_id', sa.String(36), nullable=True, index=True),
        sa.Column('tenant_id', sa.String(36), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('updated_by', sa.String(100), nullable=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
    )


def downgrade() -> None:
    op.drop_table('membrane_synced_events')
    op.drop_table('membrane_synced_emails')
    op.drop_table('membrane_connections')
