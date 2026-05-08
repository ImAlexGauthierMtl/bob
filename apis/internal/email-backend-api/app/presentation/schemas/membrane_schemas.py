"""Membrane schemas — Pydantic models for Membrane-backed connections, emails, events."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Connection schemas ───────────────────────────────────────────

class MembraneConnectionCreateRequest(BaseModel):
    user_id: str
    membrane_connection_id: str
    integration_key: str
    connection_name: Optional[str] = None
    is_active: bool = True


class MembraneConnectionResponse(BaseModel):
    id: str
    user_id: str
    membrane_connection_id: str
    integration_key: str
    connection_name: Optional[str] = None
    is_active: bool
    last_email_sync: Optional[datetime] = None
    last_calendar_sync: Optional[datetime] = None
    metadata_json: Optional[str] = None
    tenant_id: str = "default"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ── Email schemas ────────────────────────────────────────────────

class MembraneEmailUpsertRequest(BaseModel):
    membrane_connection_id: str
    user_id: str
    provider_message_id: str
    provider: str = "microsoft-outlook"
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to_addresses: Optional[list] = None
    cc_addresses: Optional[list] = None
    received_at: Optional[datetime] = None
    is_read: bool = False
    importance: str = "normal"
    has_attachments: bool = False
    attachments_meta: Optional[list] = None
    folder: str = "inbox"
    conversation_id: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None


class MembraneEmailResponse(BaseModel):
    id: str
    membrane_connection_id: str
    user_id: str
    provider_message_id: str
    provider: str
    subject: Optional[str] = None
    body_preview: Optional[str] = None
    body_html: Optional[str] = None
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to_addresses: Optional[list] = None
    cc_addresses: Optional[list] = None
    received_at: Optional[datetime] = None
    is_read: bool = False
    importance: str = "normal"
    has_attachments: bool = False
    attachments_meta: Optional[list] = None
    folder: str = "inbox"
    conversation_id: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None
    tenant_id: str = "default"
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class MembraneEmailListResponse(BaseModel):
    items: List[MembraneEmailResponse]
    total: int
    skip: int = 0
    limit: int = 50


# ── Event schemas ────────────────────────────────────────────────

class MembraneEventUpsertRequest(BaseModel):
    membrane_connection_id: str
    user_id: str
    provider_event_id: str
    provider: str = "microsoft-outlook"
    subject: Optional[str] = None
    body_html: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    organizer_email: Optional[str] = None
    organizer_name: Optional[str] = None
    attendees: Optional[list] = None
    status: str = "none"
    is_cancelled: bool = False
    recurrence: Optional[dict] = None
    online_meeting_url: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None


class MembraneEventResponse(BaseModel):
    id: str
    membrane_connection_id: str
    user_id: str
    provider_event_id: str
    provider: str
    subject: Optional[str] = None
    body_html: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: bool = False
    organizer_email: Optional[str] = None
    organizer_name: Optional[str] = None
    attendees: Optional[list] = None
    status: str = "none"
    is_cancelled: bool = False
    recurrence: Optional[dict] = None
    online_meeting_url: Optional[str] = None
    linked_contact_id: Optional[str] = None
    linked_organization_id: Optional[str] = None
    tenant_id: str = "default"
    created_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class MembraneEventListResponse(BaseModel):
    items: List[MembraneEventResponse]
    total: int
    skip: int = 0
    limit: int = 50
