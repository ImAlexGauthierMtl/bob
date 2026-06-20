"""Application ports for Bob's agent runtime."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain import InternalContext, RuntimeModelResult, RuntimeToolCall, RuntimeToolResult


class RuntimeProviderPort(Protocol):
    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        trace_id: str,
    ) -> RuntimeModelResult:
        ...


class RuntimeToolRegistryPort(Protocol):
    def list_tools(
        self,
        *,
        prompt: str,
        context: InternalContext,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ...

    async def execute(
        self,
        *,
        call: RuntimeToolCall,
        context: InternalContext,
        metadata: dict[str, Any],
    ) -> RuntimeToolResult:
        ...
