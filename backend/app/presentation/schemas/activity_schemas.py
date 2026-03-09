"""Activity schemas — Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ActivityCreate(BaseModel):
    subject: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    activity_type: Optional[str] = "TASK"
    priority: Optional[str] = "MEDIUM"
    status: Optional[str] = "PENDING"
    due_date: Optional[datetime] = None
    organization_id: Optional[str] = None
    contact_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    assigned_to: Optional[str] = None
    owner_id: Optional[str] = None


class ActivityUpdate(BaseModel):
    subject: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    activity_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    organization_id: Optional[str] = None
    contact_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    assigned_to: Optional[str] = None
    owner_id: Optional[str] = None


class ActivityResponse(BaseModel):
    id: str
    subject: str
    description: Optional[str] = None
    activity_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    organization_id: Optional[str] = None
    contact_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    assigned_to: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActivityListResponse(BaseModel):
    items: List[ActivityResponse]
    total: int
    skip: int
    limit: int
