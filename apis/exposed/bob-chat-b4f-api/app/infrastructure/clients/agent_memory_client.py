"""Internal Agent Memory backend adapter."""

from __future__ import annotations

from typing import Any, Mapping

import httpx

from app.domain import BobChatSecurityContext
from shared.services import HTTPClient, create_service_client


PRIVATE_MEMORY_TYPES = (
    "preference",
    "correction",
    "decision",
    "project_context",
    "client_context",
    "source_pointer",
    "evidence",
    "follow_up",
    "style",
)
ORGANIZATION_MEMORY_TYPES = (
    "organization_knowledge",
    "procedure",
    "project_context",
    "client_context",
    "source_pointer",
)


class AgentMemoryBackendClient:
    def __init__(self, *, client: HTTPClient | None = None) -> None:
        self.client = client or create_service_client("agent-memory~backend-api")

    async def build_context(
        self,
        *,
        query: str,
        security_context: BobChatSecurityContext,
    ) -> dict[str, Any]:
        private_memory = await self._search(
            "/internal/agent-memory/v1/search",
            query=query,
            memory_types=PRIVATE_MEMORY_TYPES,
            security_context=security_context,
        )
        organization_memory = await self._search(
            "/internal/agent-memory/v1/organization/search",
            query=query,
            memory_types=ORGANIZATION_MEMORY_TYPES,
            security_context=security_context,
            optional=True,
        )
        degraded = []
        if private_memory.get("degraded"):
            degraded.append(private_memory["degraded"])
        if organization_memory.get("degraded"):
            degraded.append(organization_memory["degraded"])
        return {
            "private": _summarize_results(private_memory.get("results", [])),
            "organization": _summarize_results(organization_memory.get("results", [])),
            "degraded": degraded,
            "source": "agent-memory-backend-api",
        }

    async def _search(
        self,
        path: str,
        *,
        query: str,
        memory_types: tuple[str, ...],
        security_context: BobChatSecurityContext,
        optional: bool = False,
    ) -> dict[str, Any]:
        request_headers = {
            "X-Session-Context": security_context.internal_session_context,
            "X-Trace-Id": security_context.trace_id,
        }
        body = {
            "query": query,
            "memory_types": list(memory_types),
            "limit": 5,
            "include_sensitive": False,
        }
        try:
            response = await self.client.post(path, json=body, headers=request_headers)
        except httpx.HTTPError as exc:
            return {"results": [], "degraded": f"memory_backend_unavailable:{exc.__class__.__name__}"}
        if response.status_code == 403 and optional:
            return {"results": [], "degraded": "organization_memory_forbidden"}
        if response.status_code >= 400:
            return {"results": [], "degraded": _error_code(response)}
        return response.json()


def _summarize_results(results: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for result in results[:5]:
        summaries.append(
            {
                "id": result.get("id"),
                "scope_type": result.get("scope_type"),
                "memory_type": result.get("memory_type"),
                "title": result.get("title"),
                "content": result.get("content"),
                "source_ref": result.get("source_ref"),
                "sensitivity": result.get("sensitivity"),
                "verified_at": result.get("verified_at"),
            }
        )
    return summaries


def _error_code(response: httpx.Response) -> str:
    if not response.content:
        return "memory_backend_rejected"
    try:
        payload = response.json()
    except ValueError:
        return "memory_backend_rejected"
    detail = payload.get("detail", payload)
    if isinstance(detail, dict):
        return str(detail.get("code") or "memory_backend_rejected")
    return "memory_backend_rejected"
