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

import hashlib
import hmac
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
import structlog

from shared.config import get_settings
from app.middleware.auth import get_current_user, require_super_admin
from app.infrastructure.external.membrane_service import (
    generate_membrane_token,
    MembraneClient,
    build_connect_url,
)
from app.infrastructure.clients.email_client import integration_settings_client
from app.presentation.schemas.membrane_schemas import (
    MembraneTokenRequest,
    MembraneTokenResponse,
    MembraneConnectionListResponse,
    MembraneIntegrationListResponse,
    MembraneActionRunRequest,
    MembraneActionRunResponse,
    MembraneWebhookPayload,
    MembraneConfigRequest,
    MembraneConfigResponse,
)

logger = structlog.get_logger(__name__)
settings = get_settings("communication")
router = APIRouter(prefix="/api/v1/membrane")

# ── Tenant Key Resolution ─────────────────────────────────────────
#
# Architecture: single Membrane workspace shared by all CDE tenants.
# Isolation between CDE tenants is enforced by prefixing the Membrane
# `tenantKey` with the CDE `tenant_id`, so two CDE tenants can never
# collide even if they reuse the same user_id / org_id namespace.
#
# tenantKey format:
#   per-user         → "t:{tenant_id}:u:{user_id}"
#   per-organization → "t:{tenant_id}:o:{org_id}"
#   per-tenant       → "t:{tenant_id}"
#
# Default scope per integration category (override via IntegrationSetting):
#   CRM (HubSpot, Salesforce, Pipedrive, Zoho, Dynamics, Attio,
#        Monday, Jira, Confluence)               → per-organization
#   Email / Calendar (Gmail, Microsoft-Outlook) → per-user
#   Files (Drive, SharePoint, OneDrive, Dropbox,
#          Box, Google-Sheets)                   → per-user
#   Messaging (Slack, Mailchimp, Quickbooks,
#              Xero, Stripe)                     → per-user

# Default scope heuristics by integration key (lowercase).
_SCOPE_PER_ORG = {
    "hubspot", "salesforce", "pipedrive", "zoho-crm", "dynamics-crm",
    "attio", "monday", "jira", "confluence",
}


def _build_tenant_key(tenant_id: str, scope: str, user_id: str, org_id: Optional[str]) -> str:
    """Build a namespaced tenantKey for Membrane.

    Always prefixes with `t:{tenant_id}` to guarantee isolation between
    CDE tenants in a shared Membrane workspace.
    """
    tenant_id = tenant_id or "default"
    if scope == "per-tenant":
        return f"t:{tenant_id}"
    if scope == "per-organization":
        target = org_id or user_id  # fallback to user if no active org
        return f"t:{tenant_id}:o:{target}" if org_id else f"t:{tenant_id}:u:{user_id}"
    # per-user (default)
    return f"t:{tenant_id}:u:{user_id}"


def _default_scope_for(integration_key: str) -> str:
    """Return the default scope_mode for an integration when no admin
    setting is configured."""
    if integration_key.lower() in _SCOPE_PER_ORG:
        return "per-organization"
    return "per-user"


async def _resolve_tenant_key(
    user: dict,
    integration_key: str,
    request_headers=None,
) -> str:
    """Determine the Membrane tenantKey for a given user + integration.

    Queries the integration_settings table to respect per-user vs
    per-organization scope configured by the tenant admin. Falls back
    to category-based heuristics if no admin setting exists.

    Always returns a `t:{tenant_id}:...` prefixed key to guarantee
    cross-tenant isolation in the shared Membrane workspace.
    """
    tenant_id = user.get("tenant_id") or "default"
    user_id = user["user_id"]
    org_id = user.get("active_organization_id")

    # Try admin-configured scope first
    try:
        setting = await integration_settings_client.get(integration_key, forward_headers=request_headers)
        if setting:
            scope = setting.get("scope_mode", _default_scope_for(integration_key))
            return _build_tenant_key(tenant_id, scope, user_id, org_id)
    except Exception:
        # Backend unavailable or setting not found — fall through to default
        pass

    # Category-based default
    scope = _default_scope_for(integration_key)
    return _build_tenant_key(tenant_id, scope, user_id, org_id)


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
    tenant_key = await _resolve_tenant_key(current_user, request.integration_key, request.headers)
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
    tenant_key = await _resolve_tenant_key(current_user, integration_key or "")
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


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    integration_key: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Disconnect a Membrane connection.

    The tenantKey is resolved exactly as for list/connect so users can only
    ever delete connections that belong to their own scope.
    """
    tenant_key = await _resolve_tenant_key(current_user, integration_key or "")
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=current_user.get("email", tenant_key),
        fields={"croo_user_id": current_user["user_id"]},
        expires_minutes=5,
    )
    client = MembraneClient(token)
    try:
        removed = await client.delete_connection(connection_id)
        logger.info(
            "membrane_connection_deleted",
            connection_id=connection_id,
            tenant_key=tenant_key,
            existed=removed,
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Connection not found")
    except httpx.HTTPStatusError as exc:
        logger.error("membrane_delete_connection_error", status=exc.response.status_code, detail=str(exc))
        raise HTTPException(status_code=502, detail="Failed to delete connection on Membrane")
    finally:
        await client.close()


@router.get("/integrations", response_model=MembraneIntegrationListResponse)
async def list_integrations(
    current_user: dict = Depends(get_current_user),
):
    """List available integrations configured in the Membrane workspace."""
    # Workspace-scoped read: use the service client token if available
    client = MembraneClient()
    try:
        raw_items = await client.list_integrations()
        # Map Membrane format to frontend-expected schema
        items = []
        for raw in raw_items:
            key = raw.get("key", "").replace("~connector.", "")
            items.append({
                "id": key,
                "key": key,
                "name": raw.get("name", key),
                "description": raw.get("description", ""),
                "iconUrl": raw.get("logoUri", ""),
                "status": "active" if not raw.get("isReadOnly", False) else "beta",
            })
        return MembraneIntegrationListResponse(items=items)
    except httpx.HTTPStatusError as exc:
        logger.error("membrane_list_integrations_error", status=exc.response.status_code)
        raise HTTPException(status_code=502, detail="Failed to fetch integrations from Membrane")
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Membrane integration not configured")
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
    tenant_key = await _resolve_tenant_key(current_user, action_key)
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
    tenant_key = await _resolve_tenant_key(current_user, integration_key)
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

def _verify_membrane_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
    """Verify a Membrane webhook using HMAC-SHA256.

    Membrane signs each webhook with the secret configured in Console →
    Admin → Manage Webhooks, and delivers the hex-encoded HMAC-SHA256 of
    the raw JSON body in the `X-Signature` header.

    The comparison is timing-safe via `hmac.compare_digest`.

    Behavior:
    - If no `MEMBRANE_WEBHOOK_SECRET` is configured, verification is
      skipped (useful for local dev). A warning is logged so prod
      deployments without a secret are easy to spot.
    - If a secret is configured but the header is missing or invalid,
      the request is rejected with 401.
    """
    secret = getattr(settings, "membrane_webhook_secret", None)
    if not secret:
        logger.warning("membrane_webhook_signature_skipped", reason="no_secret_configured")
        return True

    if not signature_header:
        return False

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    # Strip optional scheme prefix (some providers ship "sha256=...")
    received = signature_header.split("=", 1)[-1].strip()
    return hmac.compare_digest(expected, received)


@router.post("/webhook")
async def membrane_webhook(request: Request):
    """Receive webhook events from Membrane flows (email sync, calendar sync,
    CRM events, etc.).

    Security: the raw request body is verified against the `X-Signature`
    header using HMAC-SHA256 with `MEMBRANE_WEBHOOK_SECRET` before any
    processing. Invalid/missing signatures are rejected with 401.

    Membrane flows are configured in the Membrane console to send events
    to this endpoint. The payload contains the tenant_key so we can route
    to the correct Croo tenant/user/organization.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-signature") or request.headers.get("X-Signature")

    if not _verify_membrane_signature(raw_body, signature):
        logger.warning(
            "membrane_webhook_invalid_signature",
            ip=(request.client.host if request.client else None),
            has_signature=bool(signature),
        )
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        data = json.loads(raw_body)
        payload = MembraneWebhookPayload.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("membrane_webhook_invalid_payload", error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

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


# ── Platform Configuration ───────────────────────────────────────

@router.get("/config", response_model=MembraneConfigResponse)
async def get_membrane_config(
    current_user: dict = Depends(get_current_user),
):
    """Read current Membrane platform configuration (no secret returned)."""
    return MembraneConfigResponse(
        workspace_key=settings.membrane_workspace_key or "",
        api_url=settings.membrane_api_url,
        configured=bool(settings.membrane_workspace_key and settings.membrane_workspace_secret),
    )


@router.put("/config", response_model=MembraneConfigResponse)
async def update_membrane_config(
    request: MembraneConfigRequest,
    current_user: dict = Depends(require_super_admin),
):
    """Update Membrane platform credentials (super-admin only).

    This overwrites the workspace key / secret in-memory. In production,
    persist to a secrets store and restart the service.
    """
    from app.infrastructure.external.membrane_service import set_membrane_credentials

    set_membrane_credentials(
        workspace_key=request.workspace_key,
        workspace_secret=request.workspace_secret,
        api_url=request.api_url,
    )

    return MembraneConfigResponse(
        workspace_key=request.workspace_key,
        api_url=request.api_url,
        configured=bool(request.workspace_key and request.workspace_secret),
        message="Membrane configuration updated successfully",
    )
