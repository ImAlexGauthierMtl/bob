"""Integration Settings schemas — Pydantic models for per-tenant config (B4F proxy)."""

from pydantic import BaseModel
from typing import Optional, List


class IntegrationSettingCreate(BaseModel):
    integration_key: str
    scope_mode: str = "per-user"
    is_enabled: bool = True
    display_name: Optional[str] = None
    notes: Optional[str] = None


class IntegrationSettingUpdate(BaseModel):
    scope_mode: Optional[str] = None
    is_enabled: Optional[bool] = None
    display_name: Optional[str] = None
    notes: Optional[str] = None


class IntegrationSettingResponse(BaseModel):
    id: str
    integration_key: str
    scope_mode: str
    is_enabled: bool
    display_name: Optional[str] = None
    notes: Optional[str] = None
    tenant_id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class IntegrationSettingListResponse(BaseModel):
    items: List[IntegrationSettingResponse]
