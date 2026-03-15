"""Tenant schemas."""
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class TenantCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9\\-]+$")
    status: str = "TRIAL"
    plan: str = "STARTER"
    owner_email: str = Field(..., max_length=255)
    owner_name: str = Field(..., max_length=255)
    max_users: int = 5
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    settings: Optional[dict] = None
    notes: Optional[str] = None

class TenantUpdateRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    status: Optional[str] = None
    plan: Optional[str] = None
    owner_email: Optional[str] = None
    owner_name: Optional[str] = None
    max_users: Optional[int] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    settings: Optional[dict] = None
    notes: Optional[str] = None

class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    status: str
    plan: str
    owner_email: str
    owner_name: str
    max_users: int
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    settings: Optional[dict] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class TenantListResponse(BaseModel):
    items: List[TenantResponse]
    total: int
