"""Synced Email entity — local retention of M365 emails."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid
from app.domain.entities.email_contact import email_contacts


class SyncedEmail(Base, TenantMixin, AuditMixin):
    """Locally stored email from Microsoft 365 — retention strategy.

    Each email belongs to one user's MS365 connection.
    Auto-linking to CRM contacts/organizations is done by matching
    sender/recipient addresses against known contacts.
    """

    __tablename__ = "synced_emails"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Ownership
    ms365_connection_id = Column(
        String(36), ForeignKey("ms365_connections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    # Microsoft Graph identity
    ms_message_id = Column(String(255), nullable=False, unique=True, index=True, comment="MS Graph message ID")

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
    folder = Column(String(100), nullable=True, default="inbox", index=True)
    smart_label = Column(String(50), nullable=True, index=True, comment="AI-assigned category")
    ai_summary = Column(Text, nullable=True, comment="Short AI-generated summary of email content")
    ai_action_items = Column(JSON, nullable=True, comment="List of action items extracted by AI")
    conversation_id = Column(String(255), nullable=True, index=True, comment="MS Graph conversation ID for threading")

    # CRM auto-linking
    linked_contact_id = Column(String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    linked_organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)

    # Relationships
    # connection relationship — ORM back_populates commented for standalone
    # connection = relationship("MS365Connection", back_populates="synced_emails")

    # M:N with Contacts (from, to, cc)
#     linked_contacts = relationship(
#         "Contact",
#         secondary=email_contacts,
#         backref="linked_emails",
#         lazy="selectin",
#     )
