"""MS365 API Schemas."""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MS365AuthUrlResponse(BaseModel):
    """Response for auth URL generation."""
    auth_url: str


class MS365ConnectionResponse(BaseModel):
    """MS365 Connection details."""
    id: Optional[str] = None
    user_id: str
    ms_user_id: Optional[str] = None
    ms_email: Optional[str] = None
    is_active: bool
    
    class Config:
        from_attributes = True


class SyncedEmailResponse(BaseModel):
    """A synced email."""
    id: str
    subject: str
    from_address: Optional[str] = None
    from_name: Optional[str] = None
    to_addresses: Optional[List[str]] = None
    body_preview: Optional[str] = None
    body_html: Optional[str] = None
    received_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SyncedEmailListResponse(BaseModel):
    """List of synced emails."""
    items: List[SyncedEmailResponse]
    total: int
    skip: int
    limit: int


class SyncedEventResponse(BaseModel):
    """A synced calendar event."""
    id: str
    subject: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SyncedEventListResponse(BaseModel):
    """List of synced calendar events."""
    items: List[SyncedEventResponse]
    total: int
    skip: int
    limit: int


class SyncStatusResponse(BaseModel):
    """Sync status response."""
    emails_synced: int
    events_synced: int
    status: str


class EmailAiInsightResponse(BaseModel):
    """AI insights for an email."""
    summary: str
    smart_label: str
    action_items: List[str]


class SendEmailRequest(BaseModel):
    """Request to send email."""
    subject: str
    body_content: str
    to_recipients: List[str]
    cc_recipients: Optional[List[str]] = None
    bcc_recipients: Optional[List[str]] = None
    body_type: str = "html"


class ReplyEmailRequest(BaseModel):
    """Request to reply to email."""
    comment: str
    reply_all: bool = False


class ForwardEmailRequest(BaseModel):
    """Request to forward email."""
    to_recipients: List[str]
    comment: Optional[str] = None
