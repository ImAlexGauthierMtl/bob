"""MS365 Pydantic schemas — request/response models."""

from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


# ── Connection ───────────────────────────────────────────────────

class MS365AuthUrlResponse(BaseModel):
    """OAuth2 authorization URL."""
    auth_url: str


class MS365ConnectionResponse(BaseModel):
    """Connection status for the current user."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    ms_email: Optional[str] = None
    is_active: bool
    last_email_sync: Optional[datetime] = None
    last_calendar_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class MS365CallbackRequest(BaseModel):
    """OAuth2 callback — code exchange."""
    code: str
    state: Optional[str] = None


# ── Synced Emails ────────────────────────────────────────────────

class EmailAddressSchema(BaseModel):
    """Email address with display name."""
    address: Optional[str] = None
    name: Optional[str] = None


class AttachmentMetaSchema(BaseModel):
    """Attachment metadata (not content)."""
    name: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None


class SyncedEmailResponse(BaseModel):
    """Response for a synced email."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    ms_message_id: str
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to_addresses: Optional[List[dict]] = None
    cc_addresses: Optional[List[dict]] = None
    received_at: Optional[datetime] = None
    is_read: bool = False
    importance: Optional[str] = "normal"
    has_attachments: bool = False
    attachments_meta: Optional[List[dict]] = None
    folder: Optional[str] = "inbox"
    smart_label: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_action_items: Optional[List[str]] = None
    conversation_id: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("ai_action_items", mode="before")
    @classmethod
    def normalize_action_items(cls, v: object) -> object:
        if v is None:
            return v
        if isinstance(v, list):
            result = []
            for item in v:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    result.append(item.get("action", str(item)))
                else:
                    result.append(str(item))
            return result
        return v


class SyncedEmailListResponse(BaseModel):
    """Paginated list of synced emails."""
    items: List[SyncedEmailResponse]
    total: int
    skip: int
    limit: int


# ── Synced Events ────────────────────────────────────────────────

class AttendeeSchema(BaseModel):
    """Calendar event attendee."""
    email: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = "none"


class SyncedEventResponse(BaseModel):
    """Response for a synced calendar event."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    ms_event_id: str
    subject: Optional[str] = None
    body_html: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    organizer_email: Optional[str] = None
    organizer_name: Optional[str] = None
    attendees: Optional[List[dict]] = None
    status: Optional[str] = "none"
    is_cancelled: bool = False
    recurrence: Optional[dict] = None
    online_meeting_url: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SyncedEventListResponse(BaseModel):
    """Paginated list of synced calendar events."""
    items: List[SyncedEventResponse]
    total: int
    skip: int
    limit: int


# ── Sync Status ──────────────────────────────────────────────────

class SyncStatusResponse(BaseModel):
    """Result of a sync operation."""
    emails_synced: int = 0
    events_synced: int = 0
    status: str = "completed"


# ── AI Insights ──────────────────────────────────────────────────

class EmailAiInsightResponse(BaseModel):
    """AI-generated insights for an email."""
    summary: Optional[str] = None
    smart_label: Optional[str] = None
    action_items: Optional[List[str]] = None
    sentiment: Optional[str] = None
    priority_score: Optional[int] = None


# ── Actions (Send/Reply/Forward) ─────────────────────────────────

class SendEmailRequest(BaseModel):
    """Request body for sending a new email."""
    subject: str
    body_content: str
    to_recipients: List[str]
    cc_recipients: Optional[List[str]] = None
    bcc_recipients: Optional[List[str]] = None
    body_type: Optional[str] = "html"

class ReplyEmailRequest(BaseModel):
    """Request body for replying to an email."""
    comment: str
    reply_all: Optional[bool] = False

class ForwardEmailRequest(BaseModel):
    """Request body for forwarding an email."""
    to_recipients: List[str]
    comment: Optional[str] = ""
