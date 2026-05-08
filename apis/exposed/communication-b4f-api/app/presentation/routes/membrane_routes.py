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
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
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

# Built-in connectors exposed by Membrane as `~connector.<key>`. When the frontend
# sends one of these as `integration_key` (stripped of the prefix for readability),
# we must send it as `connectorKey` — not `integrationKey` — to /connect.
_WELL_KNOWN_CONNECTORS = {
    "microsoft-outlook", "gmail", "slack", "google-drive", "dropbox",
    "microsoft-sharepoint", "onedrive", "salesforce", "confluence", "hubspot",
    "zoho-crm", "dynamics-crm", "pipedrive", "monday", "google-sheets",
    "quickbooks", "attio", "jira", "xero", "mailchimp", "stripe", "github",
    "notion", "asana", "freshsales", "keap", "airtable", "bamboohr",
    "activecampaign", "sugarcrm", "outreach", "box",
}

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
        # Membrane returns camelCase keys and may use `connectorId` + `key`
        # (for direct connectors like microsoft-outlook) instead of
        # `integrationId` + `integrationKey` (for integration apps). Normalize
        # both shapes to snake_case so the frontend sees a consistent schema.
        normalized: list[dict[str, Any]] = []
        for c in items:
            key = c.get("integrationKey") or c.get("key")
            iid = c.get("integrationId") or c.get("connectorId")
            if integration_key and key != integration_key and iid != integration_key:
                continue
            normalized.append({
                "id": c.get("id"),
                "integration_id": iid,
                "integration_key": key,
                "connector_id": c.get("connectorId"),
                "name": c.get("name"),
                "disconnected": bool(c.get("disconnected", False)),
                "state": c.get("state"),
                "created_at": c.get("createdAt"),
            })
        return MembraneConnectionListResponse(items=normalized)
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
    """Return a one-shot URL that will auto-POST to Membrane /connect.

    This endpoint is Bearer-authenticated. It generates the Membrane JWT scoped
    to the current user's tenantKey and returns a URL to our public
    /connect-redirect endpoint. The returned URL contains the Membrane token in
    the query string — safe because:
      - the token is already scoped and expires in 30 min
      - it will be sent to Membrane in clear text from the browser anyway
    """
    if not redirect_uri:
        ingress = os.environ.get("INGRESS_URL", "http://localhost:4700").rstrip("/")
        redirect_uri = f"{ingress}/settings/integrations?membrane=connected&integration={integration_key}"

    tenant_key = await _resolve_tenant_key(current_user, integration_key)
    token = generate_membrane_token(
        tenant_key=tenant_key,
        name=current_user.get("email", tenant_key),
        fields={"croo_user_id": current_user["user_id"]},
        expires_minutes=30,
    )

    from urllib.parse import urlencode
    # The /connect-redirect endpoint is served by this backend (communication-b4f-api).
    # PUBLIC_API_URL points to the backend as seen from the browser (e.g. http://localhost:28004
    # in dev, https://api.croo.io in prod). Falls back to INGRESS_URL/api if not set.
    public_api = os.environ.get("PUBLIC_API_URL")
    if not public_api:
        ingress = os.environ.get("INGRESS_URL", "http://localhost:4700").rstrip("/")
        public_api = ingress
    public_api = public_api.rstrip("/")
    params = {
        "integration_key": integration_key,
        "redirect_uri": redirect_uri,
        "token": token,
    }
    url = f"{public_api}/api/v1/membrane/connect-redirect?{urlencode(params)}"
    return {"url": url, "integration_key": integration_key}


@router.get("/connect-redirect", response_class=HTMLResponse)
async def connect_redirect(
    integration_key: str,
    redirect_uri: str,
    token: str,
):
    """Serve an HTML page that auto-submits a form POST to Membrane /connect.

    Membrane's /connect is POST-only with params in form body — a simple browser
    redirect (GET) returns 404. We serve this auto-submit HTML page so the
    browser ends up making a proper POST to Membrane with the JWT in the body.

    This endpoint is PUBLIC (no Bearer auth) because the browser redirects to it
    directly. The Membrane JWT in the `token` query param carries tenant scope
    and a 30-min expiry, so leaking it in URL is no worse than the frontend
    passing it to Membrane directly.
    """
    import html as html_escape_mod
    import json as json_mod
    membrane_api = settings.membrane_api_url.rstrip("/")
    # Membrane expects everything in a JSON-stringified `payload` form field,
    # including the tenant JWT (browsers can't add an Authorization header to
    # a form POST).
    #
    # Membrane distinguishes "integrations" (custom per-workspace apps) from
    # "connectors" (built-in Microsoft/Google/etc. providers). Direct connectors
    # such as microsoft-outlook, gmail, slack expose themselves in the catalog
    # with the prefix `~connector.<key>`. When calling `/connect`, we must pass
    # those under `connectorKey`, not `integrationKey`.
    payload_data = {
        "redirectUri": redirect_uri,
        "token": token,
        # Membrane connectors can expose multiple auth options (oauth2, auth-proxy,
        # service-account, …). For built-in MS/Google connectors the hosted dashboard
        # defaults to `auth-proxy`, which brokers the OAuth flow through Membrane's
        # own credentials instead of requiring the workspace to provision an OAuth
        # app. This matches how users connect from getmembrane.com directly.
        "authOptionKey": "auth-proxy",
    }
    if integration_key.startswith("~connector.") or integration_key in _WELL_KNOWN_CONNECTORS:
        normalized = integration_key.replace("~connector.", "")
        payload_data["connectorKey"] = normalized
    else:
        payload_data["integrationKey"] = integration_key
    payload_json = json_mod.dumps(payload_data)
    html_body = f"""<!DOCTYPE html>
<html><head><meta charset=\"utf-8\"><title>Connecting to {html_escape_mod.escape(integration_key)}...</title>
<style>body {{ font-family: system-ui, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; color: #555; }}</style>
</head><body>
<div>Connecting to {html_escape_mod.escape(integration_key)}... <noscript>JavaScript is required.</noscript></div>
<form id=\"f\" method=\"POST\" action=\"{html_escape_mod.escape(membrane_api)}/connect\" enctype=\"application/x-www-form-urlencoded\">
  <input type=\"hidden\" name=\"payload\" value='{html_escape_mod.escape(payload_json)}'>
</form>
<script>document.getElementById('f').submit();</script>
</body></html>"""
    return HTMLResponse(content=html_body)


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
    """Delegate email events to the email-backend-api for persistence.

    Maps the Membrane email payload schema to MembraneEmailUpsertRequest
    and upserts via membrane_crud_client.
    """
    from app.infrastructure.clients.email_client import membrane_crud_client

    tenant_id, user_id = _parse_tenant_key(payload.tenant_key)
    d = payload.data
    membrane_conn_id = d.get("connectionId") or d.get("connection_id")

    # Look up the local membrane_connection record (create if missing)
    local_conn_id = await _resolve_local_connection(
        membrane_conn_id=membrane_conn_id,
        user_id=user_id,
        tenant_id=tenant_id,
        integration_key=payload.integration_key,
    )
    if not local_conn_id:
        logger.warning("membrane_webhook_email_no_connection", tenant_key=payload.tenant_key)
        return

    email_data = {
        "membrane_connection_id": local_conn_id,
        "user_id": user_id,
        "provider_message_id": d.get("id") or d.get("messageId") or d.get("message_id"),
        "provider": payload.integration_key,
        "subject": d.get("subject"),
        "body_preview": d.get("bodyPreview") or d.get("body_preview") or _text_preview(d.get("body")),
        "body_html": d.get("bodyHtml") or d.get("body_html") or d.get("body"),
        "from_address": _extract_address(d.get("from")),
        "from_name": _extract_name(d.get("from")),
        "to_addresses": _extract_addresses(d.get("to")),
        "cc_addresses": _extract_addresses(d.get("cc")),
        "received_at": _parse_iso(d.get("receivedAt") or d.get("received_at")),
        "is_read": bool(d.get("isRead") or d.get("is_read", False)),
        "importance": d.get("importance", "normal"),
        "has_attachments": bool(d.get("hasAttachments") or d.get("has_attachments", False)),
        "attachments_meta": d.get("attachments") or d.get("attachments_meta"),
        "folder": d.get("folder") or "inbox",
        "conversation_id": d.get("conversationId") or d.get("conversation_id"),
    }

    try:
        await membrane_crud_client.upsert_email(email_data)
        logger.info("membrane_webhook_email_persisted", provider_message_id=email_data["provider_message_id"], tenant_key=payload.tenant_key)
    except Exception as exc:
        logger.error("membrane_webhook_email_persist_failed", error=str(exc), tenant_key=payload.tenant_key)


async def _handle_event_webhook(payload: MembraneWebhookPayload):
    """Delegate calendar events to the email-backend-api."""
    from app.infrastructure.clients.email_client import membrane_crud_client

    tenant_id, user_id = _parse_tenant_key(payload.tenant_key)
    d = payload.data
    membrane_conn_id = d.get("connectionId") or d.get("connection_id")

    local_conn_id = await _resolve_local_connection(
        membrane_conn_id=membrane_conn_id,
        user_id=user_id,
        tenant_id=tenant_id,
        integration_key=payload.integration_key,
    )
    if not local_conn_id:
        logger.warning("membrane_webhook_event_no_connection", tenant_key=payload.tenant_key)
        return

    event_data = {
        "membrane_connection_id": local_conn_id,
        "user_id": user_id,
        "provider_event_id": d.get("id") or d.get("eventId") or d.get("event_id"),
        "provider": payload.integration_key,
        "subject": d.get("subject"),
        "body_html": d.get("bodyHtml") or d.get("body_html") or d.get("body"),
        "location": d.get("location"),
        "start_time": _parse_iso(d.get("start") or d.get("startTime") or d.get("start_time")),
        "end_time": _parse_iso(d.get("end") or d.get("endTime") or d.get("end_time")),
        "is_all_day": bool(d.get("isAllDay") or d.get("is_all_day", False)),
        "organizer_email": _extract_address(d.get("organizer")),
        "organizer_name": _extract_name(d.get("organizer")),
        "attendees": _extract_attendees(d.get("attendees")),
        "status": d.get("status", "none"),
        "is_cancelled": bool(d.get("isCancelled") or d.get("is_cancelled", False)),
        "recurrence": d.get("recurrence"),
        "online_meeting_url": d.get("onlineMeetingUrl") or d.get("online_meeting_url"),
    }

    try:
        await membrane_crud_client.upsert_event(event_data)
        logger.info("membrane_webhook_event_persisted", provider_event_id=event_data["provider_event_id"], tenant_key=payload.tenant_key)
    except Exception as exc:
        logger.error("membrane_webhook_event_persist_failed", error=str(exc), tenant_key=payload.tenant_key)


async def _handle_crm_webhook(payload: MembraneWebhookPayload):
    """Delegate CRM events (HubSpot deals, contacts) to the CRM backend."""
    logger.info("membrane_webhook_crm", tenant_key=payload.tenant_key, record_type=payload.data.get("type"))
    pass


# ── Helpers ──────────────────────────────────────────────────────

def _parse_tenant_key(tenant_key: str) -> tuple:
    """Parse a tenantKey back into (tenant_id, user_or_org_id).

    Expected formats:
      t:{tenant_id}:u:{user_id}
      t:{tenant_id}:o:{org_id}
      t:{tenant_id}
    """
    parts = tenant_key.split(":")
    tenant_id = parts[1] if len(parts) >= 2 else "default"
    entity_id = parts[3] if len(parts) >= 4 else ""
    return tenant_id, entity_id


async def _resolve_local_connection(
    membrane_conn_id: Optional[str],
    user_id: str,
    tenant_id: str,
    integration_key: str,
) -> Optional[str]:
    """Return the local membrane_connections.id for a given Membrane connection ID.

    If no record exists, create one via the email-backend-api so that
    subsequent webhook payloads can be linked.
    """
    from app.infrastructure.clients.email_client import membrane_crud_client
    if not membrane_conn_id:
        return None
    try:
        # Upsert a connection record (backend will update if existing)
        resp = await membrane_crud_client.upsert_connection({
            "user_id": user_id,
            "membrane_connection_id": membrane_conn_id,
            "integration_key": integration_key,
            "connection_name": integration_key,
            "is_active": True,
        })
        return resp.get("id")
    except Exception as exc:
        logger.warning("resolve_local_connection_failed", error=str(exc), membrane_conn_id=membrane_conn_id)
        return None


def _extract_address(addr: Any) -> Optional[str]:
    if not addr:
        return None
    if isinstance(addr, dict):
        return addr.get("email") or addr.get("address")
    if isinstance(addr, str):
        return addr
    return None


def _extract_name(addr: Any) -> Optional[str]:
    if not addr:
        return None
    if isinstance(addr, dict):
        return addr.get("name")
    return None


def _extract_addresses(items: Any) -> Optional[list]:
    if not items:
        return None
    if isinstance(items, list):
        return [{"address": _extract_address(i), "name": _extract_name(i)} for i in items]
    return None


def _extract_attendees(items: Any) -> Optional[list]:
    if not items:
        return None
    if isinstance(items, list):
        return [{"email": _extract_address(i), "name": _extract_name(i), "status": (i.get("status") or "none") if isinstance(i, dict) else "none"} for i in items]
    return None


def _parse_iso(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, str):
        return value
    return None


def _text_preview(html_or_text: Optional[str], max_len: int = 500) -> Optional[str]:
    if not html_or_text:
        return None
    # Naive strip of HTML tags for preview
    import re
    text = re.sub(r"<[^>]+>", " ", html_or_text)
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len] + "…"
    return text or None


# ── Frontend Proxy (email-backend-api bridge) ──────────────────

@router.get("/connections/by-user/{user_id}")
async def proxy_get_connection_by_user(
    user_id: str,
    integration_key: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Return a user's Membrane connection record from email-backend-api."""
    from app.infrastructure.clients.email_client import membrane_crud_client
    data = await membrane_crud_client.get_connection_by_user(
        user_id, integration_key=integration_key, forward_headers=current_user,
    )
    if not data:
        raise HTTPException(status_code=404, detail="Connection not found")
    return data


@router.get("/emails")
async def proxy_list_emails(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    folder: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """List Membrane-synced emails via email-backend-api."""
    from app.infrastructure.clients.email_client import membrane_crud_client
    return await membrane_crud_client.list_emails(
        user_id, skip=skip, limit=limit, folder=folder, search=search,
        forward_headers=current_user,
    )


@router.get("/events")
async def proxy_list_events(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
):
    """List Membrane-synced events via email-backend-api."""
    from app.infrastructure.clients.email_client import membrane_crud_client
    _from = from_date.isoformat() if from_date else None
    _to = to_date.isoformat() if to_date else None
    return await membrane_crud_client.list_events(
        user_id, skip=skip, limit=limit, from_date=_from, to_date=_to,
        forward_headers=current_user,
    )


# ── Platform Configuration ───────────────────────────────────────

@router.get("/config", response_model=MembraneConfigResponse)
async def get_membrane_config(
    current_user: dict = Depends(get_current_user),
):
    """Read current Membrane platform configuration.

    Never returns the workspace secret. Instead returns a `secret_configured`
    boolean so the UI can render a masked placeholder instead of an empty
    field (which is misleading — users think it's missing and try to save,
    overwriting the existing secret).
    """
    current = _get_runtime_settings()
    has_secret = bool(current.membrane_workspace_secret)
    return MembraneConfigResponse(
        workspace_key=current.membrane_workspace_key or "",
        api_url=current.membrane_api_url,
        configured=bool(current.membrane_workspace_key and has_secret),
        secret_configured=has_secret,
    )


@router.put("/config", response_model=MembraneConfigResponse)
async def update_membrane_config(
    request: MembraneConfigRequest,
    current_user: dict = Depends(require_super_admin),
):
    """Update Membrane platform credentials (super-admin only).

    Partial update semantics:
      - workspace_key and api_url are always updated from the request
      - workspace_secret is ONLY updated when the request contains a non-empty
        value — this lets the UI hide the secret (render '••••••') without
        accidentally wiping it when the super-admin just wants to rotate the
        key or change the API URL.
    """
    from app.infrastructure.external.membrane_service import (
        set_membrane_credentials,
        _get_settings as _current_settings,
    )

    current = _current_settings()
    # Treat empty string, whitespace, or a mask-only placeholder as "no change"
    incoming_secret = (request.workspace_secret or "").strip()
    is_masked = incoming_secret and set(incoming_secret) <= {"•", "*", " "}
    effective_secret = (
        current.membrane_workspace_secret
        if not incoming_secret or is_masked
        else incoming_secret
    )

    set_membrane_credentials(
        workspace_key=request.workspace_key,
        workspace_secret=effective_secret,
        api_url=request.api_url,
    )

    return MembraneConfigResponse(
        workspace_key=request.workspace_key,
        api_url=request.api_url,
        configured=bool(request.workspace_key and effective_secret),
        secret_configured=bool(effective_secret),
        message="Membrane configuration updated successfully",
    )


def _get_runtime_settings():
    """Fetch the current (possibly UI-overridden) Membrane settings."""
    from app.infrastructure.external.membrane_service import _get_settings as _cur
    return _cur()
