"""Pipedream Connect client.

Provider integrations are owned by the backend. The frontend receives only
short-lived Connect tokens or hosted Connect Link URLs.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
import structlog
from shared.config import get_settings

logger = structlog.get_logger(__name__)

_settings = None


def _get_settings():
    global _settings
    if _settings is None:
        _settings = get_settings("email-backend")
    return _settings


def set_pipedream_credentials(
    client_id: str,
    client_secret: str,
    project_id: str,
    environment: str,
    api_url: str,
) -> None:
    """Update the runtime Pipedream credentials."""
    global _settings
    current = _get_settings()
    _settings = current.model_copy(update={
        "pipedream_client_id": client_id,
        "pipedream_client_secret": client_secret,
        "pipedream_project_id": project_id,
        "pipedream_environment": environment,
        "pipedream_api_url": api_url,
    })
    logger.info(
        "pipedream_credentials_updated",
        project_id=project_id,
        environment=environment,
        has_client_id=bool(client_id),
        has_secret=bool(client_secret),
    )


class PipedreamClient:
    """Low-level async client for Pipedream Connect API."""

    def __init__(self) -> None:
        settings = _get_settings()
        self._base = settings.pipedream_api_url.rstrip("/")
        self._project_id = settings.pipedream_project_id
        self._environment = settings.pipedream_environment
        self._client_id = settings.pipedream_client_id
        self._client_secret = settings.pipedream_client_secret
        if not self._client_id or not self._client_secret or not self._project_id:
            raise RuntimeError("Pipedream credentials not configured")
        self._client = httpx.AsyncClient(timeout=60.0)
        self._access_token: Optional[str] = None
        self._access_token_expires_at: Optional[datetime] = None

    async def _get_access_token(self) -> str:
        if self._access_token and self._access_token_expires_at:
            if datetime.now(timezone.utc) < self._access_token_expires_at:
                return self._access_token

        response = await self._client.post(
            f"{self._base}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "connect:*",
            },
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        expires_in = int(payload.get("expires_in") or 3600)
        self._access_token = payload["access_token"]
        self._access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(30, expires_in - 60))
        return self._access_token

    async def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {await self._get_access_token()}",
            "Content-Type": "application/json",
            "x-pd-environment": self._environment,
        }

    async def create_connect_token(
        self,
        external_user_id: str,
        *,
        allowed_origins: Optional[list[str]] = None,
        success_redirect_uri: Optional[str] = None,
        error_redirect_uri: Optional[str] = None,
        webhook_uri: Optional[str] = None,
        expires_in: int = 3600,
        scope: str = "connect:accounts:read connect:accounts:write connect:actions:* connect:proxy",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "external_user_id": external_user_id,
            "expires_in": expires_in,
            "scope": scope,
        }
        if allowed_origins:
            body["allowed_origins"] = allowed_origins
        if success_redirect_uri:
            body["success_redirect_uri"] = success_redirect_uri
        if error_redirect_uri:
            body["error_redirect_uri"] = error_redirect_uri
        if webhook_uri:
            body["webhook_uri"] = webhook_uri

        response = await self._client.post(
            f"{self._base}/connect/{self._project_id}/tokens",
            json=body,
            headers=await self._headers(),
        )
        response.raise_for_status()
        return response.json()

    async def list_accounts(self, external_user_id: str, app: Optional[str] = None) -> list[dict[str, Any]]:
        params = {"app": app} if app else None
        response = await self._client.get(
            f"{self._base}/connect/{self._project_id}/users/{external_user_id}/accounts",
            params=params,
            headers=await self._headers(),
        )
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, list) else data.get("data", [])

    async def list_apps(
        self,
        query: Optional[str] = None,
        limit: int = 100,
        *,
        after: Optional[str] = None,
        has_actions: Optional[bool] = None,
        has_triggers: Optional[bool] = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["q"] = query
        if after:
            params["after"] = after
        if has_actions is not None:
            params["has_actions"] = str(has_actions).lower()
        if has_triggers is not None:
            params["has_triggers"] = str(has_triggers).lower()
        response = await self._client.get(
            f"{self._base}/connect/apps",
            params=params,
            headers=await self._headers(),
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"data": payload}

    async def list_actions(
        self,
        app: str,
        query: Optional[str] = None,
        limit: int = 20,
        *,
        after: Optional[str] = None,
        registry: str = "public",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"app": app, "limit": limit, "registry": registry}
        if query:
            params["q"] = query
        if after:
            params["after"] = after
        response = await self._client.get(
            f"{self._base}/connect/{self._project_id}/actions",
            params=params,
            headers=await self._headers(),
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {"data": payload}

    async def delete_account(self, account_id: str) -> bool:
        response = await self._client.delete(
            f"{self._base}/connect/{self._project_id}/accounts/{account_id}",
            headers=await self._headers(),
        )
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    async def run_action(
        self,
        action_id: str,
        external_user_id: str,
        configured_props: dict[str, Any],
        *,
        version: Optional[str] = None,
        dynamic_props_id: Optional[str] = None,
        stash_id: Optional[str] = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "id": action_id,
            "external_user_id": external_user_id,
            "configured_props": configured_props,
        }
        if version:
            body["version"] = version
        if dynamic_props_id:
            body["dynamic_props_id"] = dynamic_props_id
        if stash_id:
            body["stash_id"] = stash_id

        response = await self._client.post(
            f"{self._base}/connect/{self._project_id}/actions/run",
            json=body,
            headers=await self._headers(),
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
