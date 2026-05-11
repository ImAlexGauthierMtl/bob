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
    # Membrane connections may be tied to an integration app (`integrationId` /
    # `integrationKey`), a direct connector (`connectorId` / `key`), or an
    # external app. We keep both shapes optional and let the frontend pick
    # whichever is present.
    integration_id: Optional[str] = None
    integration_key: Optional[str] = None
    connector_id: Optional[str] = None
    name: Optional[str] = None
    disconnected: bool = False
    state: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"extra": "allow", "populate_by_name": True}


class MembraneConnectionListResponse(BaseModel):
    items: List[MembraneConnectionResponse]


# ── Integration ──────────────────────────────────────────────────

class MembraneIntegrationResponse(BaseModel):
    id: str
    key: str
    name: str
    iconUrl: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"


class MembraneIntegrationListResponse(BaseModel):
    items: List[MembraneIntegrationResponse]


# ── Action ───────────────────────────────────────────────────────

class MembraneActionRunRequest(BaseModel):
    action_key: Optional[str] = None
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


# ── Platform Configuration (managed via UI) ───────────────────────

class MembraneConfigRequest(BaseModel):
    workspace_key: str
    # Optional — omit or pass empty/None to keep the existing secret unchanged.
    # Must never be rendered back to the UI for safety.
    workspace_secret: Optional[str] = None
    api_url: str = "https://api.getmembrane.com"


class MembraneConfigResponse(BaseModel):
    workspace_key: str
    api_url: str
    configured: bool
    # Explicit flag so the UI can show a masked placeholder ("••••••••") when a
    # secret is already configured — distinguishes "never set" from "set but hidden".
    secret_configured: bool = False
    message: Optional[str] = None
