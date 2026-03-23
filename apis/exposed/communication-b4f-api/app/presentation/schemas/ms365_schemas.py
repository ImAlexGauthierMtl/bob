"""MS365 API Schemas."""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class MS365AuthUrlResponse(BaseModel):
    auth_url: str


class MS365ConnectionResponse(BaseModel):
    id: Optional[str] = None
    user_id: str
    ms_user_id: Optional[str] = None
    ms_email: Optional[str] = None
    is_active: bool
    last_email_sync: Optional[datetime] = None
    last_calendar_sync: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EmailAddressSchema(BaseModel):
    address: Optional[str] = None
    name: Optional[str] = None


class AttachmentMetaSchema(BaseModel):
    name: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None


class SyncedEmailResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    ms_message_id: Optional[str] = None
    subject: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to_addresses: Optional[List[EmailAddressSchema]] = None
    cc_addresses: Optional[List[EmailAddressSchema]] = None
    body_preview: Optional[str] = None
    body_html: Optional[str] = None
    received_at: Optional[datetime] = None
    is_read: bool = False
    importance: Optional[str] = "normal"
    has_attachments: bool = False
    attachments_meta: Optional[List[AttachmentMetaSchema]] = None
    folder: Optional[str] = None
    conversation_id: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None
    smart_label: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_action_items: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SyncedEmailListResponse(BaseModel):
    items: List[SyncedEmailResponse]
    total: int
    skip: int
    limit: int


class AttendeeSchema(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None


class SyncedEventResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    ms_event_id: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    organizer_email: Optional[str] = None
    organizer_name: Optional[str] = None
    attendees: Optional[List[AttendeeSchema]] = None
    status: Optional[str] = None
    is_cancelled: bool = False
    recurrence: Optional[Any] = None
    online_meeting_url: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SyncedEventListResponse(BaseModel):
    items: List[SyncedEventResponse]
    total: int
    skip: int
    limit: int


class SyncStatusResponse(BaseModel):
    emails_synced: int
    events_synced: int
    status: str


class EmailAiInsightResponse(BaseModel):
    summary: str
    smart_label: str
    action_items: List[str]


class SendEmailRequest(BaseModel):
    subject: str
    body_content: str
    to_recipients: List[str]
    cc_recipients: Optional[List[str]] = None
    bcc_recipients: Optional[List[str]] = None
    body_type: str = "html"


class ReplyEmailRequest(BaseModel):
    comment: str
    reply_all: bool = False


class ForwardEmailRequest(BaseModel):
    to_recipients: List[str]
    comment: Optional[str] = None
