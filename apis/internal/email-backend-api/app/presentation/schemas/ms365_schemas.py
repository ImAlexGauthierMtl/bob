"""MS365 schemas — Pydantic models for connections, emails, events."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Connection schemas ───────────────────────────────────────────

class ConnectionCreateRequest(BaseModel):
    user_id: str
    ms_user_id: Optional[str] = None
    ms_email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scopes: Optional[str] = None
    is_active: bool = True


class ConnectionUpdateRequest(BaseModel):
    ms_user_id: Optional[str] = None
    ms_email: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scopes: Optional[str] = None
    is_active: Optional[bool] = None
    last_email_sync: Optional[datetime] = None
    last_calendar_sync: Optional[datetime] = None
    email_delta_token: Optional[str] = None
    calendar_delta_token: Optional[str] = None
    email_webhook_subscription_id: Optional[str] = None
    email_webhook_expiration: Optional[datetime] = None
    calendar_webhook_subscription_id: Optional[str] = None
    calendar_webhook_expiration: Optional[datetime] = None


class ConnectionResponse(BaseModel):
    id: str
    user_id: str
    ms_user_id: Optional[str] = None
    ms_email: Optional[str] = None
    is_active: bool
    last_email_sync: Optional[datetime] = None
    last_calendar_sync: Optional[datetime] = None
    email_webhook_subscription_id: Optional[str] = None
    calendar_webhook_subscription_id: Optional[str] = None
    tenant_id: str = "default"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class ConnectionDetailResponse(ConnectionResponse):
    """Includes token fields for internal B4F calls."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scopes: Optional[str] = None
    email_delta_token: Optional[str] = None
    calendar_delta_token: Optional[str] = None


# ── Email schemas ────────────────────────────────────────────────

class EmailUpsertRequest(BaseModel):
    ms365_connection_id: str
    user_id: str
    ms_message_id: str
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to_addresses: Optional[list] = None
    cc_addresses: Optional[list] = None
    received_at: Optional[datetime] = None
    is_read: bool = False
    importance: Optional[str] = "normal"
    has_attachments: bool = False
    attachments_meta: Optional[list] = None
    folder: Optional[str] = "inbox"
    smart_label: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_action_items: Optional[list] = None
    conversation_id: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None


class EmailUpdateRequest(BaseModel):
    is_read: Optional[bool] = None
    folder: Optional[str] = None
    smart_label: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_action_items: Optional[list] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None


class EmailResponse(BaseModel):
    id: str
    ms365_connection_id: str
    user_id: str
    ms_message_id: str
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to_addresses: Optional[list] = None
    cc_addresses: Optional[list] = None
    received_at: Optional[datetime] = None
    is_read: bool = False
    importance: Optional[str] = "normal"
    has_attachments: bool = False
    attachments_meta: Optional[list] = None
    folder: Optional[str] = "inbox"
    smart_label: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_action_items: Optional[list] = None
    conversation_id: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None
    tenant_id: str = "default"
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class EmailListResponse(BaseModel):
    items: List[EmailResponse]
    total: int
    skip: int = 0
    limit: int = 50


# ── Event schemas ────────────────────────────────────────────────

class EventUpsertRequest(BaseModel):
    ms365_connection_id: str
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
    attendees: Optional[list] = None
    status: Optional[str] = "none"
    is_cancelled: bool = False
    recurrence: Optional[dict] = None
    online_meeting_url: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None


class EventUpdateRequest(BaseModel):
    subject: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    is_cancelled: Optional[bool] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None


class EventResponse(BaseModel):
    id: str
    ms365_connection_id: str
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
    attendees: Optional[list] = None
    status: Optional[str] = "none"
    is_cancelled: bool = False
    recurrence: Optional[dict] = None
    online_meeting_url: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None
    tenant_id: str = "default"
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    items: List[EventResponse]
    total: int
    skip: int = 0
    limit: int = 50


# ── Email Contact link schemas ───────────────────────────────────

class EmailContactLinkRequest(BaseModel):
    contact_id: str
    role: str = "from"


class EmailContactLinkResponse(BaseModel):
    id: str
    synced_email_id: str
    contact_id: str
    role: str
