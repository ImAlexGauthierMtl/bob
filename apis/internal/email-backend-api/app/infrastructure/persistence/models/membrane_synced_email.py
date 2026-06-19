"""Membrane Synced Email entity — stores emails ingested via Membrane webhooks."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid


class MembraneSyncedEmail(Base, TenantMixin, AuditMixin):
    """Locally stored email received via Membrane sync/webhooks.

    Mirrors SyncedEmail schema but is linked to membrane_connections
    instead of ms365_connections. This lets legacy and Membrane data
    coexist during the transition period.
    """

    __tablename__ = "membrane_synced_emails"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Ownership
    membrane_connection_id = Column(
        String(36),
        ForeignKey("membrane_connections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(String(36), nullable=False, index=True,
                     comment="Soft ref to user service users.id")

    # Provider identity (e.g. MS Graph message id, Gmail thread id)
    provider_message_id = Column(
        String(255), nullable=False, unique=True, index=True,
        comment="Provider-level unique message ID",
    )
    provider = Column(
        String(50), nullable=False, default="microsoft-outlook",
        comment="Source provider, e.g. microsoft-outlook, gmail",
    )

    # Email content
    subject = Column(String(500), nullable=True, index=True)
    body_preview = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)

    # Sender
    from_address = Column(String(255), nullable=True, index=True)
    from_name = Column(String(255), nullable=True)

    # Recipients
    to_addresses = Column(JSON, nullable=True, comment="List of {address, name} dicts")
    cc_addresses = Column(JSON, nullable=True)

    # Metadata
    received_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_read = Column(Boolean, default=False, nullable=False)
    importance = Column(String(20), nullable=True, default="normal")
    has_attachments = Column(Boolean, default=False, nullable=False)
    attachments_meta = Column(JSON, nullable=True, comment="List of {name, size, contentType} dicts")
    folder = Column(String(255), nullable=True, default="inbox", index=True)
    conversation_id = Column(String(255), nullable=True, index=True)

    # CRM auto-linking
    linked_contact_id = Column(String(36), nullable=True, index=True,
                               comment="Soft ref to contact service contacts.id")
    linked_organization_id = Column(String(36), nullable=True, index=True,
                                    comment="Soft ref to organization service organizations.id")
