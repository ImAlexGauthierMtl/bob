"""Membrane schemas — Pydantic models for token generation and connections."""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List


# ── Token ──────────────────────────────────────────────────────────

class MembraneTokenRequest(BaseModel):
    integration_key: str


class MembraneTokenResponse(BaseModel):
    token: str
    expires_at: str


# ── Connection ───────────────────────────────────────────────────

class MembraneConnectionResponse(BaseModel):
    id: str
    integration_id: str
    integration_key: str
    name: str
    disconnected: bool
    created_at: Optional[str] = None


class MembraneConnectionListResponse(BaseModel):
    items: List[MembraneConnectionResponse]


# ── Integration ──────────────────────────────────────────────────

class MembraneIntegrationResponse(BaseModel):
    id: str
    key: str
    name: str
    logo_uri: Optional[str] = None
    description: Optional[str] = None


class MembraneIntegrationListResponse(BaseModel):
    items: List[MembraneIntegrationResponse]


# ── Action ───────────────────────────────────────────────────────

class MembraneActionRunRequest(BaseModel):
    action_key: str
    connection_id: Optional[str] = None
    input: Dict[str, Any] = {}


class MembraneActionRunResponse(BaseModel):
    success: bool
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ── Webhook (inbound from Membrane flows) ────────────────────────

class MembraneWebhookPayload(BaseModel):
    event_type: str
    connection_id: str
    integration_key: str
    tenant_key: str
    data: Dict[str, Any]
    timestamp: Optional[str] = None
