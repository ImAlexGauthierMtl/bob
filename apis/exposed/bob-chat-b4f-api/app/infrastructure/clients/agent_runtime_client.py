"""Internal Agent Runtime backend adapter."""

from __future__ import annotations

from typing import Any, Mapping

import httpx

from app.domain import BobChatIntegrationError, BobChatNotFoundError, BobChatSecurityContext
from shared.services import HTTPClient, create_service_client


class AgentRuntimeBackendClient:
    def __init__(self, *, client: HTTPClient | None = None) -> None:
        self.client = client or create_service_client("agent-runtime~backend-api")

    async def create_run(
        self,
        *,
        session_id: str,
        input_message_id: str,
        prompt: str,
        channel: str,
        metadata: Mapping[str, Any],
        security_context: BobChatSecurityContext,
        idempotency_key: str,
    ) -> dict[str, Any]:
        response = await self._call(
            "post",
            "/internal/agent-runtime/v1/runs",
            security_context=security_context,
            headers={"Idempotency-Key": idempotency_key},
            json={
                "session_id": session_id,
                "input_message_id": input_message_id,
                "prompt": prompt,
                "channel": channel,
                "metadata": dict(metadata),
            },
        )
        return _json(response)

    async def confirm_confirmation(
        self,
        *,
        run_id: str,
        confirmation_id: str,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        return await self._resolve_confirmation(
            run_id=run_id,
            confirmation_id=confirmation_id,
            decision="confirm",
            security_context=security_context,
        )

    async def cancel_confirmation(
        self,
        *,
        run_id: str,
        confirmation_id: str,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        return await self._resolve_confirmation(
            run_id=run_id,
            confirmation_id=confirmation_id,
            decision="cancel",
            security_context=security_context,
        )

    async def _resolve_confirmation(
        self,
        *,
        run_id: str,
        confirmation_id: str,
        decision: str,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        response = await self._call(
            "post",
            f"/internal/agent-runtime/v1/runs/{run_id}/confirmations/{confirmation_id}/{decision}",
            security_context=security_context,
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
                "agent_runtime_backend_unavailable",
                status_code=503,
                detail={"code": "agent_runtime_backend_unavailable", "message": str(exc)},
            ) from exc

        _raise_for_status(response)
        return response


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    detail = _safe_detail(response)
    if response.status_code == 404:
        raise BobChatNotFoundError(
            "runtime_resource_not_found",
            status_code=404,
            detail=detail,
        )
    raise BobChatIntegrationError(
        "agent_runtime_backend_rejected",
        status_code=response.status_code,
        detail=detail,
    )


def _safe_detail(response: httpx.Response) -> Any:
    if not response.content:
        return {"code": "agent_runtime_backend_error"}
    try:
        payload = response.json()
    except ValueError:
        return {"code": "agent_runtime_backend_error", "message": response.text}
    return payload.get("detail", payload)


def _json(response: httpx.Response) -> dict[str, Any]:
    if response.status_code == 204 or not response.content:
        return {}
    return response.json()
