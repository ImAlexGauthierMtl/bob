"""Bob Cloud identity adapter for Bob Chat."""

from __future__ import annotations

from typing import Any

import httpx

from app.domain import BOB_CHAT_CAPABILITY, BobChatIntegrationError, BobChatSecurityContext
from shared.infrastructure import InternalSessionContext, InternalSessionContextSigner
from shared.services import BobCloudClient, BobCloudResponseError


class BobCloudIdentityProvider:
    def __init__(
        self,
        *,
        bob_cloud_client: BobCloudClient,
        signer: InternalSessionContextSigner,
    ) -> None:
        self.bob_cloud_client = bob_cloud_client
        self.signer = signer

    async def resolve(
        self,
        *,
        forward_headers: Any,
        trace_id: str,
    ) -> BobChatSecurityContext:
        try:
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
