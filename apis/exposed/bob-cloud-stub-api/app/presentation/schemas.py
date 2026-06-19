"""HTTP schemas for Bob Cloud stub routes."""

from typing import Literal

from pydantic import BaseModel, Field


class CapabilityCheckRequest(BaseModel):
    capability: str = Field(..., min_length=1, max_length=160)


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    status: Literal["active", "suspended", "disabled"] | None = None
    hierarchy_path: str | None = Field(default=None, min_length=1, max_length=240)
    scope: str | None = Field(default=None, min_length=1, max_length=80)


class LicenseUpdateRequest(BaseModel):
    status: Literal["enabled", "disabled", "preview"] | None = None
    remaining: int | None = Field(default=None, ge=0)
    limit: int | None = Field(default=None, ge=0)


class InvitationRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    tenant_id: str | None = Field(default=None, min_length=1, max_length=120)
    role_codes: list[str] | None = None


class MembershipUpdateRequest(BaseModel):
    role_codes: list[str] | None = None
    status: Literal["active", "pending", "disabled"] | None = None
