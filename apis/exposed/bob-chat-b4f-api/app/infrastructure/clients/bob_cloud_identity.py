"""Bob Cloud identity adapter for Bob Chat."""

from __future__ import annotations

import os
from typing import Any

import httpx

from app.domain import BOB_CHAT_CAPABILITY, BobChatIntegrationError, BobChatSecurityContext
from shared.infrastructure import InternalSessionContext, InternalSessionContextSigner
from shared.services import BobCloudClient, BobCloudResponseError, HTTPClient, create_service_client


class BobCloudIdentityProvider:
    def __init__(
        self,
        *,
        bob_cloud_client: BobCloudClient,
        signer: InternalSessionContextSigner,
        local_auth_client: HTTPClient | None = None,
    ) -> None:
        self.bob_cloud_client = bob_cloud_client
        self.signer = signer
        self.local_auth_client = local_auth_client

    async def resolve(
        self,
        *,
        forward_headers: Any,
        trace_id: str,
    ) -> BobChatSecurityContext:
        try:
            local_session = await self._local_session(forward_headers)
            if local_session is not None:
                session = local_session
                capability = _local_capability(session)
            else:
                session = await self.bob_cloud_client.get_session(forward_headers=forward_headers)
                capability = await self.bob_cloud_client.check_capability(
                    BOB_CHAT_CAPABILITY,
                    forward_headers=forward_headers,
                )
        except BobCloudResponseError as exc:
            raise BobChatIntegrationError(
                "bob_cloud_rejected",
                status_code=exc.status_code,
                detail=exc.detail,
            ) from exc
        except httpx.HTTPError as exc:
            raise BobChatIntegrationError(
                "bob_cloud_unavailable",
                status_code=503,
                detail={"code": "bob_cloud_unavailable", "message": str(exc)},
            ) from exc

        if not session.get("authenticated"):
            raise BobChatIntegrationError(
                "not_authenticated",
                status_code=401,
                detail={"code": "not_authenticated"},
            )
        if capability.get("status") != "enabled":
            raise BobChatIntegrationError(
                "capability_denied",
                status_code=403,
                detail={"code": capability.get("reason_code") or "capability_denied"},
            )

        user = session.get("user") or {}
        tenant = session.get("tenant") or {}
        user_id = str(user.get("id") or "")
        tenant_id = str(tenant.get("id") or "")
        bob_session_id = str(session.get("session_id") or "")
        if not user_id or not tenant_id or not bob_session_id:
            raise BobChatIntegrationError(
                "not_authenticated",
                status_code=401,
                detail={"code": "not_authenticated"},
            )

        context = InternalSessionContext(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=bob_session_id,
            trace_id=trace_id,
            permissions=tuple(str(item) for item in session.get("permissions", []) if item),
            entitlements=(BOB_CHAT_CAPABILITY,),
            roles=tuple(str(item) for item in session.get("platform_roles", []) if item),
        )
        return BobChatSecurityContext(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=bob_session_id,
            trace_id=trace_id,
            internal_session_context=self.signer.issue(context),
        )

    async def _local_session(self, forward_headers: Any) -> dict[str, Any] | None:
        if not _local_auth_enabled() or not _bearer_token(forward_headers):
            return None

        client = self.local_auth_client or create_service_client("auth~b4f-api")
        try:
            response = await client.get("/api/auth/v1/session", forward_headers=forward_headers)
        except httpx.HTTPError as exc:
            raise BobChatIntegrationError(
                "local_auth_unavailable",
                status_code=503,
                detail={"code": "local_auth_unavailable", "message": str(exc)},
            ) from exc
        if response.status_code >= 400:
            raise BobChatIntegrationError(
                "local_auth_rejected",
                status_code=response.status_code,
                detail=_response_detail(response),
            )
        return response.json() if response.content else {}


def _local_auth_enabled() -> bool:
    configured = os.environ.get("CDE_LOCAL_AUTH_ENABLED")
    if configured is not None:
        return configured.lower() in {"1", "true", "yes", "on"}
    environment = os.environ.get("ENV", os.environ.get("ENVIRONMENT", "development")).lower()
    return environment in {"development", "dev", "local", "test", "ci"}


def _bearer_token(headers: Any) -> str | None:
    if not headers:
        return None
    mapping = headers if isinstance(headers, dict) else dict(headers)
    authorization = str(mapping.get("authorization") or mapping.get("Authorization") or "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _local_capability(session: dict[str, Any]) -> dict[str, Any]:
    permissions = {str(item) for item in session.get("permissions", []) if item}
    roles = {str(item).lower() for item in session.get("platform_roles", []) if item}
    if BOB_CHAT_CAPABILITY in permissions or roles.intersection({"admin", "super_admin", "owner"}):
        return {"capability": BOB_CHAT_CAPABILITY, "status": "enabled"}
    return {"capability": BOB_CHAT_CAPABILITY, "status": "denied", "reason_code": "capability_denied"}


def _response_detail(response: httpx.Response) -> Any:
    if not response.content:
        return {"code": "local_auth_rejected"}
    try:
        payload = response.json()
    except ValueError:
        return {"code": "local_auth_rejected", "message": response.text}
    return payload.get("detail", payload)
