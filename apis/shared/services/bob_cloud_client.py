"""Client for the Bob Cloud contract consumed by CDE.

The client is intentionally thin: it centralizes transport, headers, and mode
guards, while business authorization remains in the calling B4F/backend layer.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping, Optional

import httpx

BOB_CLOUD_ALLOWED_MODES = {"real", "stub"}
PRODUCTION_ENVS = {"prod", "production"}
DEFAULT_STUB_URL = "http://bob-cloud-stub-api:8010"

BOB_CLOUD_FORWARD_HEADERS = {
    "authorization",
    "cookie",
    "idempotency-key",
    "traceparent",
    "x-correlation-id",
    "x-request-id",
    "x-session-context",
    "x-trace-id",
}


class BobCloudClientError(Exception):
    """Base error for Bob Cloud client failures."""


class BobCloudModeError(BobCloudClientError):
    """Raised when Bob Cloud mode or URL configuration is unsafe."""


class BobCloudResponseError(BobCloudClientError):
    """Raised when Bob Cloud returns a non-success HTTP status."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: Any,
        path: str,
        method: str,
    ) -> None:
        super().__init__(f"Bob Cloud {method} {path} failed with status {status_code}")
        self.status_code = status_code
        self.detail = detail
        self.path = path
        self.method = method


def _normalize_mode(mode: str) -> str:
    normalized = mode.strip().lower()
    if normalized not in BOB_CLOUD_ALLOWED_MODES:
        raise BobCloudModeError("BOB_CLOUD_MODE must be one of: real, stub")
    return normalized


def _normalize_environment(environment: str) -> str:
    return environment.strip().lower()


def _ensure_stub_not_production(mode: str, environment: str) -> None:
    if mode == "stub" and environment in PRODUCTION_ENVS:
        raise BobCloudModeError("BOB_CLOUD_MODE=stub is forbidden in production")


@dataclass(frozen=True)
class BobCloudClientConfig:
    """Transport configuration for the Bob Cloud adapter."""

    base_url: str
    mode: str = "real"
    environment: str = "development"
    timeout: float = 10.0

    def __post_init__(self) -> None:
        normalized_mode = _normalize_mode(self.mode)
        normalized_environment = _normalize_environment(self.environment)
        if not self.base_url.strip():
            raise BobCloudModeError("Bob Cloud base_url is required")
        _ensure_stub_not_production(normalized_mode, normalized_environment)
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))
        object.__setattr__(self, "mode", normalized_mode)
        object.__setattr__(self, "environment", normalized_environment)


def create_bob_cloud_client_from_env(
    *,
    transport: Optional[httpx.AsyncBaseTransport] = None,
    timeout: Optional[float] = None,
) -> "BobCloudClient":
    """Create a Bob Cloud client from environment variables.

    `real` mode requires an explicit `BOB_CLOUD_API_URL`; `stub` mode defaults
    to the docker-compose service and is rejected in production environments.
    """

    mode = _normalize_mode(os.environ.get("BOB_CLOUD_MODE", "real"))
    environment = _normalize_environment(
        os.environ.get("ENV", os.environ.get("ENVIRONMENT", "development"))
    )
    _ensure_stub_not_production(mode, environment)

    if mode == "stub":
        base_url = (
            os.environ.get("BOB_CLOUD_API_URL")
            or os.environ.get("BOB_CLOUD_STUB_API_URL")
            or DEFAULT_STUB_URL
        )
    else:
        base_url = os.environ.get("BOB_CLOUD_API_URL")
        if not base_url:
            raise BobCloudModeError("BOB_CLOUD_API_URL is required when BOB_CLOUD_MODE=real")

    config = BobCloudClientConfig(
        base_url=base_url,
        mode=mode,
        environment=environment,
        timeout=timeout or float(os.environ.get("BOB_CLOUD_TIMEOUT_SECONDS", "10")),
    )
    return BobCloudClient(config=config, transport=transport)


class BobCloudClient:
    """Async adapter for the Bob Cloud endpoints consumed by CDE."""

    def __init__(
        self,
        *,
        config: BobCloudClientConfig,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.config = config
        self._transport = transport

    async def get_session(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request("GET", "/api/auth/v1/session", forward_headers=forward_headers)

    async def get_session_response(self, *, forward_headers: Optional[Any] = None) -> httpx.Response:
        return await self._request_response("GET", "/api/auth/v1/session", forward_headers=forward_headers)

    async def refresh_session(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request("POST", "/api/auth/v1/refresh", forward_headers=forward_headers)

    async def refresh_session_response(self, *, forward_headers: Optional[Any] = None) -> httpx.Response:
        return await self._request_response("POST", "/api/auth/v1/refresh", forward_headers=forward_headers)

    async def logout(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request("POST", "/api/auth/v1/logout", forward_headers=forward_headers)

    async def logout_response(self, *, forward_headers: Optional[Any] = None) -> httpx.Response:
        return await self._request_response("POST", "/api/auth/v1/logout", forward_headers=forward_headers)

    async def get_entitlements(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/platform/v1/entitlements/me",
            forward_headers=forward_headers,
        )

    async def check_capability(
        self,
        capability: str,
        *,
        forward_headers: Optional[Any] = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/platform/v1/entitlements/check",
            json={"capability": capability},
            forward_headers=forward_headers,
        )

    async def get_current_tenant(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/platform/v1/tenants/current",
            forward_headers=forward_headers,
        )

    async def list_tenants(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/platform/v1/tenants",
            forward_headers=forward_headers,
        )

    async def update_tenant(
        self,
        tenant_id: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
        forward_headers: Optional[Any] = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/platform/v1/tenants/{tenant_id}",
            json=dict(payload),
            headers={"Idempotency-Key": idempotency_key},
            forward_headers=forward_headers,
        )

    async def list_licenses(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/api/platform/v1/licenses",
            forward_headers=forward_headers,
        )

    async def update_license(
        self,
        capability: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
        forward_headers: Optional[Any] = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/platform/v1/licenses/{capability}",
            json=dict(payload),
            headers={"Idempotency-Key": idempotency_key},
            forward_headers=forward_headers,
        )

    async def list_users(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request("GET", "/api/iam/v1/users", forward_headers=forward_headers)

    async def create_invitation(
        self,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
        forward_headers: Optional[Any] = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/iam/v1/invitations",
            json=dict(payload),
            headers={"Idempotency-Key": idempotency_key},
            forward_headers=forward_headers,
        )

    async def list_roles(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request("GET", "/api/iam/v1/roles", forward_headers=forward_headers)

    async def list_memberships(self, *, forward_headers: Optional[Any] = None) -> dict[str, Any]:
        return await self._request("GET", "/api/iam/v1/memberships", forward_headers=forward_headers)

    async def update_membership(
        self,
        membership_id: str,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str,
        forward_headers: Optional[Any] = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/api/iam/v1/memberships/{membership_id}",
            json=dict(payload),
            headers={"Idempotency-Key": idempotency_key},
            forward_headers=forward_headers,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Any] = None,
        headers: Optional[Mapping[str, str]] = None,
        forward_headers: Optional[Any] = None,
    ) -> dict[str, Any]:
        response = await self._request_response(
            method,
            path,
            json=json,
            headers=headers,
            forward_headers=forward_headers,
        )

        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    async def _request_response(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Any] = None,
        headers: Optional[Mapping[str, str]] = None,
        forward_headers: Optional[Any] = None,
    ) -> httpx.Response:
        request_headers = self._build_headers(headers=headers, forward_headers=forward_headers)
        async with httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout,
            transport=self._transport,
        ) as client:
            response = await client.request(
                method,
                path,
                json=json,
                headers=request_headers,
            )

        if response.status_code >= 400:
            raise BobCloudResponseError(
                status_code=response.status_code,
                detail=self._read_detail(response),
                path=path,
                method=method,
            )

        return response

    def _build_headers(
        self,
        *,
        headers: Optional[Mapping[str, str]] = None,
        forward_headers: Optional[Any] = None,
    ) -> dict[str, str]:
        result: dict[str, str] = {"Accept": "application/json"}
        if forward_headers:
            mapping = forward_headers if isinstance(forward_headers, Mapping) else dict(forward_headers)
            for key, value in mapping.items():
                if key.lower() in BOB_CLOUD_FORWARD_HEADERS and value:
                    result[key] = value
        if headers:
            for key, value in headers.items():
                if not value:
                    continue
                for existing_key in list(result):
                    if existing_key.lower() == key.lower():
                        del result[existing_key]
                result[key] = value
        return result

    @staticmethod
    def _read_detail(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text
