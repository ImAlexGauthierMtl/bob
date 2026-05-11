"""Membrane integration client — REST API wrapper for getmembrane.com.

Handles token generation, connection management, action proxying, and webhook
reception. All calls to Membrane are authenticated with per-tenant JWTs generated
on the Croo backend.
"""

import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

import httpx
import structlog
from jose import jwt
from shared.config import get_settings

logger = structlog.get_logger(__name__)

_settings = None


def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings("communication")
    return _settings


def set_membrane_credentials(workspace_key: str, workspace_secret: str, api_url: str, client_token: Optional[str] = None):
    """Update the global Membrane credentials at runtime (e.g. from UI config)."""
    global _settings
    current = _get_settings()
    _settings = current.model_copy(update={
        "membrane_workspace_key": workspace_key,
        "membrane_workspace_secret": workspace_secret,
        "membrane_api_url": api_url,
    })
    if client_token:
        _settings = _settings.model_copy(update={"membrane_client_token": client_token})
    logger.info("membrane_credentials_updated", api_url=api_url, has_key=bool(workspace_key), has_client_token=bool(client_token))


# ── JWT Token Generation ─────────────────────────────────────────

def generate_membrane_token(
    tenant_key: str,
    name: str,
    fields: Optional[Dict[str, Any]] = None,
    expires_minutes: int = 120,
) -> str:
    """Generate a signed JWT for Membrane scoped to a specific tenantKey.

    The tenant_key maps to a Croo entity (user_id, org_id, or tenant_id)
    depending on the integration scope_mode configured by the admin.
    """
    settings = _get_settings()
    if not settings.membrane_workspace_key or not settings.membrane_workspace_secret:
        raise RuntimeError("Membrane workspace credentials not configured")

    now = datetime.now(timezone.utc)
    payload = {
        "workspaceKey": settings.membrane_workspace_key,
        "tenantKey": tenant_key,
        "name": name,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
    }
    if fields:
        payload["fields"] = fields

    return jwt.encode(
        payload,
        settings.membrane_workspace_secret,
        algorithm="HS512",
    )


# ── REST Client ──────────────────────────────────────────────────

class MembraneClient:
    """Low-level REST client for Membrane API."""

    def __init__(self, token: Optional[str] = None):
        settings = _get_settings()
        self._base = settings.membrane_api_url.rstrip("/")
        # Prefer an explicit token; fall back to a service-level client token
        effective_token = token or getattr(settings, "membrane_client_token", None)
        if not effective_token:
            raise RuntimeError("No Membrane token available (tenant or client token required)")
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {effective_token}", "Content-Type": "application/json"},
            timeout=60.0,
        )

    async def list_integrations(self) -> List[Dict[str, Any]]:
        resp = await self._client.get(f"{self._base}/integrations")
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def list_connections(self) -> List[Dict[str, Any]]:
        resp = await self._client.get(f"{self._base}/connections")
        resp.raise_for_status()
        return resp.json().get("items", [])

    async def get_connection(self, connection_id: str) -> Optional[Dict[str, Any]]:
        resp = await self._client.get(f"{self._base}/connections/{connection_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def run_action(
        self,
        action_key: str,
        input_data: Dict[str, Any],
        connection_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a Membrane action (e.g. send-email, create-deal)."""
        url = f"{self._base}/actions/{action_key}/run"
        params = {}
        if connection_id:
            params["connectionId"] = connection_id
        resp = await self._client.post(url, params=params, json=input_data)
        resp.raise_for_status()
        return resp.json()

    async def delete_connection(self, connection_id: str) -> bool:
        """Delete (disconnect) a Membrane connection by ID.

        Returns True if the connection was removed, False if it didn't exist.
        """
        resp = await self._client.delete(f"{self._base}/connections/{connection_id}")
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return True

    async def proxy_get(self, connection_id: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call a proxied GET on the underlying connector's API."""
        path = path.lstrip("/")
        url = f"{self._base}/connections/{connection_id}/proxy/{path}"
        resp = await self._client.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()

    async def proxy_post(self, connection_id: str, path: str, json_body: Dict[str, Any]) -> Dict[str, Any]:
        """Call a proxied POST on the underlying connector's API (e.g. sendMail, reply, forward)."""
        path = path.lstrip("/")
        url = f"{self._base}/connections/{connection_id}/proxy/{path}"
        resp = await self._client.post(url, json=json_body)
        resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    async def close(self):
        await self._client.aclose()


# ── URL Builders (for frontend redirect flows) ───────────────────

def build_connect_url(integration_key: str, token: str, redirect_uri: str) -> str:
    """Build a Membrane `/connect` URL for the frontend to redirect the user to.

    Docs: https://docs.getmembrane.com/docs/ways-to-use-membrane/embedded-ui/connection-ui/connection-ui-without-the-front-end-sdk
    The `/connect` endpoint handles OAuth2/OAuth1/client-credentials/proxy flows and
    redirects the browser to `redirectUri` when done (with ?connectionId=... on success
    or ?error=... on failure).
    """
    from urllib.parse import quote
    settings = _get_settings()
    base = settings.membrane_api_url.rstrip("/")
    return (
        f"{base}/connect"
        f"?integrationKey={quote(integration_key)}"
        f"&token={quote(token)}"
        f"&redirectUri={quote(redirect_uri)}"
    )


def build_reconnect_url(connection_id: str, token: str, redirect_uri: str) -> str:
    """Build a reconnect URL — reuses /connect with connectionId to update credentials."""
    from urllib.parse import quote
    settings = _get_settings()
    base = settings.membrane_api_url.rstrip("/")
    return (
        f"{base}/connect"
        f"?connectionId={quote(connection_id)}"
        f"&token={quote(token)}"
        f"&redirectUri={quote(redirect_uri)}"
    )
