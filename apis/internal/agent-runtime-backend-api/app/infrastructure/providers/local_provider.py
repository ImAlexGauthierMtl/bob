"""Local deterministic runtime provider for dev and CI."""

from __future__ import annotations

from typing import Any

from app.application.ports import RuntimeProviderPort
from app.domain import RuntimeModelResult, RuntimeToolCall


class LocalRuntimeProvider(RuntimeProviderPort):
    def __init__(self) -> None:
        self.model = "bob-local-runtime"

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        trace_id: str,
    ) -> RuntimeModelResult:
        if tools and not _has_tool_result(messages):
            return RuntimeModelResult(
                content="",
                provider="local",
                model=self.model,
                mode="local_runtime",
                tool_calls=[
                    RuntimeToolCall(
                        id="local_tool_runtime_status",
                        name="bob_runtime_status",
                        arguments={"include_tools": True},
                    )
                ],
                raw_metadata={"trace_id": trace_id, "phase": "tool_selection"},
            )

        prompt = _last_user_prompt(messages)
        tool_readback = _tool_readback(messages)
        return RuntimeModelResult(
            content=(
                "Bob fonctionne dans le runtime agentique CDE. "
                f"Demande recue: {prompt}. "
                f"Readback outils: {tool_readback}"
            ),
            provider="local",
            model=self.model,
            mode="local_runtime",
            raw_metadata={"trace_id": trace_id, "phase": "final"},
        )


def _has_tool_result(messages: list[dict[str, Any]]) -> bool:
    return any(message.get("role") == "tool" for message in messages)


def _last_user_prompt(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return " ".join(str(message.get("content") or "").split())[:180]
    return ""


def _tool_readback(messages: list[dict[str, Any]]) -> str:
    tool_messages = [str(message.get("content") or "") for message in messages if message.get("role") == "tool"]
    if not tool_messages:
        return "aucun outil requis"
    return " | ".join(item[:240] for item in tool_messages)
