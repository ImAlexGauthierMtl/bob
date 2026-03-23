"""Synced Event entity — local retention of M365 calendar events."""

from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid


class SyncedEvent(Base, TenantMixin, AuditMixin):
    """Locally stored calendar event from Microsoft 365 — retention strategy.

    Each event belongs to one user's MS365 connection.
    Auto-linking to CRM contacts/organizations via attendee matching.
    """

    __tablename__ = "synced_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Ownership
    ms365_connection_id = Column(
        String(36), ForeignKey("ms365_connections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    user_id = Column(String(36), nullable=False, index=True, comment="Soft ref to user-backend-api users.id")

    # Microsoft Graph identity
    ms_event_id = Column(String(255), nullable=False, unique=True, index=True, comment="MS Graph event ID")

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
    status = Column(String(50), nullable=True, default="none", comment="User response: accepted/tentative/declined/none")
    is_cancelled = Column(Boolean, default=False, nullable=False)

    # Recurrence
    recurrence = Column(JSON, nullable=True, comment="Recurrence pattern from MS Graph")

    # Online meeting
    online_meeting_url = Column(Text, nullable=True, comment="Teams/Zoom meeting link")

    # CRM auto-linking
    linked_contact_id = Column(String(36), nullable=True, index=True, comment="Soft ref to contact-backend-api contacts.id")
    linked_organization_id = Column(String(36), nullable=True, index=True, comment="Soft ref to org-backend-api organizations.id")
