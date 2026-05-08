"""Membrane integration routes — token generation, connection proxy, action proxy,
and webhook reception for getmembrane.com integration platform.

Architecture:
- JWT tokens are generated on the backend (never on the frontend) and scoped
  to a tenantKey that maps to user_id, org_id, or tenant_id depending on the
  integration's configured scope_mode.
- Connections are managed by Membrane; Croo proxies listing/status to the UI.
- Actions (send-email, create-deal, etc.) are proxied through Croo backend so
  we can log, transform, and fallback if needed.
- Webhooks from Membrane flows are received here and delegated to the
  email-backend-api for persistence.
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
import structlog

from shared.config import get_settings
from app.middleware.auth import get_current_user
from app.infrastructure.external.membrane_service import (
    generate_membrane_token,
    MembraneClient,
    build_connect_url,
)
from app.presentation.schemas.membrane_schemas import (
    MembraneTokenRequest,
    MembraneTokenResponse,
    MembraneConnectionListResponse,
    MembraneIntegrationListResponse,
    MembraneActionRunRequest,
    MembraneActionRunResponse,
    MembraneWebhookPayload,
)

logger = structlog.get_logger(__name__)
settings = get_settings("communication")
router = APIRouter(prefix="/api/v1/membrane")

# ── Tenant Key Resolution ─────────────────────────────────────────

def _resolve_tenant_key(
    user: dict,
    integration_key: str,
) -> str:
    """Determine the Membrane tenantKey for a given user + integration.

    In the future this will look up integration_settings table to respect
    per-user vs per-organization scope configured by the tenant admin.
    For Phase 1, we default to per-user for email integrations and
    per-organization for CRM integrations.
    """
    # TODO: query integration_settings table once it exists
    crm_keys = {"hubspot", "salesforce", "pipedrive", "zoho-crm"}
    if integration_key.lower() in crm_keys:
        org_id = user.get("active_organization_id")
        if org_id:
            return org_id
    # Default to per-user for everything else (email, calendar, etc.)
    return user["user_id"]


# ── Token Generation ───────────────────────────────────────────

@router.post("/token", response_model=MembraneTokenResponse)
async def create_membrane_token(
    request: MembraneTokenRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate a signed JWT for Membrane scoped to the current user/entity.

    The frontend calls this before opening a Membrane connection popup.
    The token is short-lived (2h) and contains no secrets.
    """
    tenant_key = _resolve_tenant_key(current_user, request.integration_key)
    name = current_user.get("email", tenant_key)
    fields = {
        "croo_user_id": current_user["user_id"],
        "croo_tenant_id": current_user.get("tenant_id", "default"),
        "croo_email": current_user.get("email"),
    }
    if current_user.get("active_organization_id"):
        fields["croo_active_org_id"] = current_user["active_organization_id"]

    try:
        token = generate_membrane_token(
            tenant_key=tenant_key,
            name=name,
            fields=fields,
        )
    except RuntimeError as exc:
        logger.error("membrane_token_generation_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Membrane integration not configured")

    from datetime import timedelta
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=120)).isoformat()
    logger.info("membrane_token_generated", tenant_key=tenant_key, integration_key=request.integration_key)
    return MembraneTokenResponse(token=token, expires_at=expires_at)


# ── Connection Management ────────────────────────────────────────

@router.get("/connections", response_model=MembraneConnectionListResponse)
async def list_connections(
    integration_key: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List Membrane connections for the current scoped tenant."""
    tenant_key = _resolve_tenant_key(current_user, integration_key or "")
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=current_user.get("email", tenant_key),
        fields={"croo_user_id": current_user["user_id"]},
        expires_minutes=5,
    )
    client = MembraneClient(token)
    try:
        items = await client.list_connections()
        # Optionally filter by integration_key client-side
        if integration_key:
            items = [
                c for c in items
                if c.get("integrationKey") == integration_key or c.get("integrationId") == integration_key
            ]
        return MembraneConnectionListResponse(items=items)
    except httpx.HTTPStatusError as exc:
        logger.error("membrane_list_connections_error", status=exc.response.status_code, detail=str(exc))
        raise HTTPException(status_code=502, detail="Failed to fetch connections from Membrane")
    finally:
        await client.close()


@router.get("/integrations", response_model=MembraneIntegrationListResponse)
async def list_integrations(
    current_user: dict = Depends(get_current_user),
):
    """List available integrations configured in the Membrane workspace."""
    # Use a generic tenant key for workspace-scoped reads; any valid token works
    token = generate_membrane_token(
        tenant_key=current_user["user_id"],
        name=current_user.get("email", "system"),
        expires_minutes=5,
    )
    client = MembraneClient(token)
    try:
        items = await client.list_integrations()
        return MembraneIntegrationListResponse(items=items)
    except httpx.HTTPStatusError as exc:
        logger.error("membrane_list_integrations_error", status=exc.response.status_code)
        raise HTTPException(status_code=502, detail="Failed to fetch integrations from Membrane")
    finally:
        await client.close()


# ── Action Proxy ─────────────────────────────────────────────────

@router.post("/actions/{action_key}/run", response_model=MembraneActionRunResponse)
async def run_action(
    action_key: str,
    body: MembraneActionRunRequest,
    current_user: dict = Depends(get_current_user),
):
    """Proxy an action run through Membrane.

    Examples:
      - action_key = "send-email"  (universal or integration-level)
      - action_key = "create-deal" (HubSpot integration-level)
    The backend resolves the correct connection automatically based on the
    tenantKey derived from the integration context.
    """
    # Derive tenant_key from the action's integration context
    # For simplicity we use a heuristic: if connection_id provided, use it
    # directly; otherwise resolve from action_key prefix or lookup.
    tenant_key = _resolve_tenant_key(current_user, action_key)
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=current_user.get("email", tenant_key),
        fields={"croo_user_id": current_user["user_id"]},
        expires_minutes=10,
    )
    client = MembraneClient(token)
    try:
        result = await client.run_action(
            action_key=action_key,
            input_data=body.input,
            connection_id=body.connection_id,
        )
        logger.info("membrane_action_run", action_key=action_key, tenant_key=tenant_key)
        return MembraneActionRunResponse(success=True, output=result)
    except httpx.HTTPStatusError as exc:
        detail = "Action execution failed"
        try:
            detail = exc.response.json().get("message", detail)
        except Exception:
            detail = exc.response.text[:200]
        logger.error("membrane_action_run_error", action_key=action_key, status=exc.response.status_code, detail=detail)
        raise HTTPException(status_code=exc.response.status_code, detail=detail)
    finally:
        await client.close()


# ── Hosted Connection URLs ───────────────────────────────────────

@router.get("/connect-url")
async def get_connect_url(
    integration_key: str,
    redirect_uri: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Return a hosted Membrane connection URL for the frontend to redirect to.

    This avoids embedding the React SDK if we prefer a redirect flow.
    """
    tenant_key = _resolve_tenant_key(current_user, integration_key)
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=current_user.get("email", tenant_key),
        fields={"croo_user_id": current_user["user_id"]},
        expires_minutes=30,
    )
    if not redirect_uri:
        ingress = os.environ.get("INGRESS_URL", "http://localhost:4700").rstrip("/")
        redirect_uri = f"{ingress}/settings/integrations?membrane=connected&integration={integration_key}"
    url = build_connect_url(integration_key, token, redirect_uri)
    return {"url": url, "integration_key": integration_key}


# ── Webhook Reception ────────────────────────────────────────────

@router.post("/webhook")
async def membrane_webhook(
    payload: MembraneWebhookPayload,
    request: Request,
):
    """Receive webhook events from Membrane flows (email sync, calendar sync,
    CRM events, etc.).

    Membrane flows are configured in the Membrane console to send events
    to this endpoint. The payload contains the tenant_key so we can route
    to the correct Croo tenant/user/organization.
    """
    logger.info(
        "membrane_webhook_received",
        event_type=payload.event_type,
        tenant_key=payload.tenant_key,
        integration_key=payload.integration_key,
    )

    # Route to the appropriate internal handler
    event_type = payload.event_type
    if event_type in {"email-received", "email-sent", "email-updated"}:
        await _handle_email_webhook(payload)
    elif event_type in {"event-created", "event-updated", "event-deleted"}:
        await _handle_event_webhook(payload)
    elif event_type in {"contact-created", "deal-created", "deal-updated"}:
        await _handle_crm_webhook(payload)
    else:
        logger.warning("membrane_webhook_unhandled_type", event_type=event_type)

    return {"status": "ok"}


async def _handle_email_webhook(payload: MembraneWebhookPayload):
    """Delegate email events to the email-backend-api for persistence."""
    from app.infrastructure.clients.email_client import email_crud_client
    # Build an upsert request from the Membrane payload
    # TODO: map Membrane email schema to Croo synced_email schema
    logger.info("membrane_webhook_email", tenant_key=payload.tenant_key, message_id=payload.data.get("id"))
    # Future: call email_crud_client.upsert() with mapped data
    pass


async def _handle_event_webhook(payload: MembraneWebhookPayload):
    """Delegate calendar events to the email-backend-api."""
    logger.info("membrane_webhook_event", tenant_key=payload.tenant_key, event_id=payload.data.get("id"))
    pass


async def _handle_crm_webhook(payload: MembraneWebhookPayload):
    """Delegate CRM events (HubSpot deals, contacts) to the CRM backend."""
    logger.info("membrane_webhook_crm", tenant_key=payload.tenant_key, record_type=payload.data.get("type"))
    pass
