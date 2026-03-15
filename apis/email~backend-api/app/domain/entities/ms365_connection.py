"""MS365 Connection entity — per-user OAuth token storage."""

import enum

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from shared.database import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class MS365Connection(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Per-user Microsoft 365 OAuth connection.

    Each user connects their own M365 account. Tokens are stored
    for delegated access via MS Graph API.
    """

    __tablename__ = "ms365_connections"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Owner
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)

    # Microsoft identity
    ms_user_id = Column(String(255), nullable=True, comment="Microsoft user object ID")
    ms_email = Column(String(255), nullable=True, comment="Microsoft email address")

    # OAuth tokens (should be encrypted at rest via DB-level or app-level encryption)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text, nullable=True, comment="Granted OAuth scopes, space-separated")

    # Connection state
    is_active = Column(Boolean, default=True, nullable=False)

    # Sync state — delta tokens for incremental sync
    last_email_sync = Column(DateTime(timezone=True), nullable=True)
    last_calendar_sync = Column(DateTime(timezone=True), nullable=True)
    email_delta_token = Column(Text, nullable=True, comment="MS Graph delta token for emails")
    calendar_delta_token = Column(Text, nullable=True, comment="MS Graph delta token for calendar")

    # Webhook subscription
    email_webhook_subscription_id = Column(String(255), nullable=True)
    email_webhook_expiration = Column(DateTime(timezone=True), nullable=True)
    calendar_webhook_subscription_id = Column(String(255), nullable=True)
    calendar_webhook_expiration = Column(DateTime(timezone=True), nullable=True)
