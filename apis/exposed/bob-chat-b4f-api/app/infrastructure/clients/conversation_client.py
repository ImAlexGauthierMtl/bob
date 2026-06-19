"""Internal conversation backend adapter."""

from __future__ import annotations

from typing import Any, Mapping

import httpx

from app.domain import (
    BobChatIntegrationError,
    BobChatNotFoundError,
    BobChatSecurityContext,
    ConversationSessionDraft,
)
from shared.services import HTTPClient, create_service_client


class ConversationBackendClient:
    def __init__(self, *, client: HTTPClient | None = None) -> None:
        self.client = client or create_service_client("conversation~backend-api")

    async def create_session(
        self,
        *,
        draft: ConversationSessionDraft,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        response = await self._call(
            "post",
            "/internal/conversation/v1/sessions",
            security_context=security_context,
            json={
                "title": draft.title,
                "channel": draft.channel,
                "mission": draft.mission,
                "client_context": draft.client_context,
            },
        )
        return _json(response)

    async def list_sessions(
        self,
        *,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        response = await self._call(
            "get",
            "/internal/conversation/v1/sessions",
            security_context=security_context,
        )
        return _json(response)

    async def get_session(
        self,
        *,
        session_id: str,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        response = await self._call(
            "get",
            f"/internal/conversation/v1/sessions/{session_id}",
            security_context=security_context,
        )
        return _json(response)

    async def delete_session(
        self,
        *,
        session_id: str,
        security_context: BobChatSecurityContext,
    ) -> None:
        await self._call(
            "delete",
            f"/internal/conversation/v1/sessions/{session_id}",
            security_context=security_context,
        )

    async def add_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        security_context: BobChatSecurityContext,
        idempotency_key: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._call(
            "post",
            f"/internal/conversation/v1/sessions/{session_id}/messages",
            security_context=security_context,
            headers={"Idempotency-Key": idempotency_key},
            json={"role": role, "content": content, "metadata": dict(metadata or {})},
        )
        return _json(response)

    async def _call(
        self,
        method: str,
        path: str,
        *,
        security_context: BobChatSecurityContext,
        headers: Mapping[str, str] | None = None,
        json: Any | None = None,
    ) -> httpx.Response:
        request_headers = {
            "X-Session-Context": security_context.internal_session_context,
            "X-Trace-Id": security_context.trace_id,
            **dict(headers or {}),
        }
        try:
            caller = getattr(self.client, method)
            if json is None:
                response = await caller(path, headers=request_headers)
            else:
                response = await caller(path, json=json, headers=request_headers)
        except httpx.HTTPError as exc:
            raise BobChatIntegrationError(
                "conversation_backend_unavailable",
                status_code=503,
                detail={"code": "conversation_backend_unavailable", "message": str(exc)},
            ) from exc

        _raise_for_status(response)
        return response


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    detail = _safe_detail(response)
    if response.status_code == 404:
        raise BobChatNotFoundError(
            "session_not_found",
            status_code=404,
            detail=detail,
        )
    raise BobChatIntegrationError(
        "conversation_backend_rejected",
        status_code=response.status_code,
        detail=detail,
    )


def _safe_detail(response: httpx.Response) -> Any:
    if not response.content:
        return {"code": "conversation_backend_error"}
    try:
        payload = response.json()
    except ValueError:
        return {"code": "conversation_backend_error", "message": response.text}
    return payload.get("detail", payload)


def _json(response: httpx.Response) -> dict[str, Any]:
    if response.status_code == 204 or not response.content:
        return {}
    return response.json()
