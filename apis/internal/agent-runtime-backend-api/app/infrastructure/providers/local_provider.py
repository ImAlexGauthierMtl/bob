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
            prompt = _last_user_prompt(messages)
            if _needs_mcp_gateway(prompt):
                if _needs_factory_read_execution(prompt):
                    return RuntimeModelResult(
                        content="",
                        provider="local",
                        model=self.model,
                        mode="local_runtime",
                        tool_calls=[
                            RuntimeToolCall(
                                id="local_tool_mcp_factory_read",
                                name="bob_mcp_gateway",
                                arguments={
                                    "operation": "execute_capability",
                                    "family": "factory",
                                    "capability": _infer_factory_read_capability(prompt),
                                    "status": _infer_factory_status(prompt),
                                    "limit": 5,
                                    "risk": "read",
                                },
                            )
                        ],
                        raw_metadata={"trace_id": trace_id, "phase": "tool_selection"},
                    )
                return RuntimeModelResult(
                    content="",
                    provider="local",
                    model=self.model,
                    mode="local_runtime",
                    tool_calls=[
                        RuntimeToolCall(
                            id="local_tool_mcp_gateway",
                            name="bob_mcp_gateway",
                            arguments={
                                "operation": "describe_family",
                                "family": _infer_mcp_family(prompt),
                                "risk": "read",
                            },
                        )
                    ],
                    raw_metadata={"trace_id": trace_id, "phase": "tool_selection"},
                )
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


def _needs_mcp_gateway(prompt: str) -> bool:
    normalized = prompt.lower()
    return any(
        token in normalized
        for token in (
            "mcp",
            "factory",
            "zoho",
            "slack",
            "teams",
            "gitlab",
            "browser",
            "skyswitch",
            "capabilit",
            "famille",
        )
    )


def _infer_mcp_family(prompt: str) -> str:
    normalized = prompt.lower()
    for family in (
        "assistant-memory",
        "support-memory",
        "croo-connect",
        "mail-calendar",
        "workspace-files",
        "pipedream-supabase",
        "gitlab-code",
        "web-research",
        "skyswitch",
        "factory",
        "zoho",
        "slack",
        "teams",
        "browser",
    ):
        if family in normalized or family.replace("-", " ") in normalized:
            return family
    return "factory"


def _needs_factory_read_execution(prompt: str) -> bool:
    normalized = prompt.lower()
    return "factory" in normalized and any(
        token in normalized
        for token in (
            "liste",
            "list",
            "queue",
            "demandes",
            "requests",
            "validation",
            "supabase",
            "execute",
            "exécute",
        )
    )


def _infer_factory_read_capability(prompt: str) -> str:
    normalized = prompt.lower()
    if "list_queue_by_project" in normalized or "queue_by_project" in normalized:
        return "requests-queues.list_queue_by_project"
    if "dev_validation" in normalized or "dev validation" in normalized or "validation" in normalized:
        return "dev-validation.list_queue"
    if "list_requests" in normalized:
        return "requests-queues.list_requests"
    if "demande" in normalized or "request" in normalized:
        return "requests-queues.list_requests"
    return "requests-queues.list_queue_by_project"


def _infer_factory_status(prompt: str) -> str:
    normalized = prompt.lower()
    if "dev_validation" in normalized or "dev validation" in normalized or "validation" in normalized:
        return "DEV_VALIDATION"
    if "todo" in normalized:
        return "TODO"
    if "business" in normalized:
        return "BUSINESS_ANALYSIS"
    return "NEW"


def _tool_readback(messages: list[dict[str, Any]]) -> str:
    tool_messages = [
        f"{message.get('name') or 'tool'}={message.get('content') or ''}"
        for message in messages
        if message.get("role") == "tool"
    ]
    if not tool_messages:
        return "aucun outil requis"
    return " | ".join(item[:240] for item in tool_messages)
