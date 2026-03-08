"""Pydantic schemas for Tenant CRUD operations."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class CamelModel(BaseModel):
    """Base model with camelCase JSON aliases."""

    model_config = ConfigDict(populate_by_name=True)


# ── Create ──────────────────────────────────────────────────

class TenantCreate(CamelModel):
    """Schema for creating a new tenant."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9\-]+$")
    status: str = Field(default="TRIAL")
    plan: str = Field(default="STARTER")
    owner_email: str = Field(..., max_length=255)
    owner_name: str = Field(..., max_length=255)
    max_users: int = Field(default=5, ge=1)
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    settings: Optional[dict] = None
    notes: Optional[str] = None


# ── Update ──────────────────────────────────────────────────

class TenantUpdate(CamelModel):
    """Schema for updating a tenant (all fields optional)."""

    name: Optional[str] = Field(None, max_length=255)
    slug: Optional[str] = Field(None, max_length=100, pattern=r"^[a-z0-9\-]+$")
    status: Optional[str] = None
    plan: Optional[str] = None
    owner_email: Optional[str] = Field(None, max_length=255)
    owner_name: Optional[str] = Field(None, max_length=255)
    max_users: Optional[int] = Field(None, ge=1)
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None
    settings: Optional[dict] = None
    notes: Optional[str] = None


# ── Response ────────────────────────────────────────────────

class TenantResponse(CamelModel):
    """Schema for tenant API responses."""

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


# ── List ────────────────────────────────────────────────────

class TenantListResponse(CamelModel):
    """Paginated list response."""

    items: List[TenantResponse]
    total: int


# ── Provision ───────────────────────────────────────────────

class TenantProvisionRequest(CamelModel):
    """Schema for provisioning a tenant's first admin user."""

    admin_email: str = Field(..., max_length=255)
    admin_password: str = Field(..., min_length=8)
    admin_first_name: str = Field(..., max_length=100)
    admin_last_name: str = Field(..., max_length=100)
