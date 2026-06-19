"""Membrane Synced Event entity — stores calendar events ingested via Membrane webhooks."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid


class MembraneSyncedEvent(Base, TenantMixin, AuditMixin):
    """Locally stored calendar event received via Membrane sync/webhooks.

    Mirrors SyncedEvent schema but is linked to membrane_connections
    instead of ms365_connections.
    """

    __tablename__ = "membrane_synced_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Ownership
    membrane_connection_id = Column(
        String(36),
        ForeignKey("membrane_connections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(String(36), nullable=False, index=True,
                     comment="Soft ref to user service users.id")

    # Provider identity
    provider_event_id = Column(
        String(255), nullable=False, unique=True, index=True,
        comment="Provider-level unique event ID",
    )
    provider = Column(
        String(50), nullable=False, default="microsoft-outlook",
        comment="Source provider, e.g. microsoft-outlook, google-calendar",
    )

    # Event content
    subject = Column(String(500), nullable=True, index=True)
    body_html = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)

    # Timing
    start_time = Column(DateTime(timezone=True), nullable=True, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    is_all_day = Column(Boolean, default=False, nullable=False)

    # Organizer
    organizer_email = Column(String(255), nullable=True, index=True)
    organizer_name = Column(String(255), nullable=True)

    # Participants
    attendees = Column(JSON, nullable=True, comment="List of {email, name, status} dicts")

    # Status
    status = Column(String(50), nullable=True, default="none")
    is_cancelled = Column(Boolean, default=False, nullable=False)

    # Recurrence + online meeting
    recurrence = Column(JSON, nullable=True)
    online_meeting_url = Column(Text, nullable=True)

    # CRM auto-linking
    linked_contact_id = Column(String(36), nullable=True, index=True)
    linked_organization_id = Column(String(36), nullable=True, index=True)
