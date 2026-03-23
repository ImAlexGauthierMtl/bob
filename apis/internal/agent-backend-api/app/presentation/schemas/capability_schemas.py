"""Capability schemas — Pydantic models."""

from pydantic import BaseModel
from typing import Optional, List


class CapabilityDefinitionResponse(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    scope: str
    module: Optional[str] = None
    default_enabled: bool
    risk_level: str

    class Config:
        from_attributes = True


class UserCapabilityAssign(BaseModel):
    capability_code: str
    granted: bool = True


class UserCapabilityResponse(BaseModel):
    code: str
    name: str
    scope: str
    module: Optional[str] = None
    risk_level: str
    granted: bool
    source: str  # system | department | user


class UserCapabilitiesResponse(BaseModel):
    user_id: str
    agent_mode: str  # suggest | approval | auto
    trust_score: float
    capabilities: List[UserCapabilityResponse]
