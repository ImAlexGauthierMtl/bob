"""Controlled local tool registry for Bob runtime."""

from __future__ import annotations

import json
from typing import Any

from app.application.ports import RuntimeToolRegistryPort
from app.domain import InternalContext, RuntimeToolCall, RuntimeToolResult


class LocalRuntimeToolRegistry(RuntimeToolRegistryPort):
    def list_tools(
        self,
        *,
        prompt: str,
        context: InternalContext,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            _function_tool(
                name="bob_runtime_status",
                description="Retourne l'etat controle du runtime Bob, du provider actif et des familles d'outils disponibles.",
                properties={
                    "include_tools": {
                        "type": "boolean",
                        "description": "Inclure un apercu des familles d'outils disponibles.",
                    }
                },
            ),
            _function_tool(
                name="bob_memory_context_summary",
                description="Resume le contexte memoire deja fourni par Bob Chat avant l'appel runtime.",
                properties={
                    "max_items": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 8,
                        "description": "Nombre maximal d'elements memoire a resumer.",
                    }
                },
            ),
        ]

    async def execute(
        self,
        *,
        call: RuntimeToolCall,
        context: InternalContext,
        metadata: dict[str, Any],
    ) -> RuntimeToolResult:
        if call.name == "bob_runtime_status":
            content = {
                "runtime": "bob-agent-runtime",
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "permissions": list(context.permissions),
                "available_tool_families": [
                    "runtime",
                    "memory",
                    "support",
                    "workspace",
                    "integrations",
                ],
                "policy": {
                    "secrets_redacted": True,
                    "write_requires_confirmation": True,
                    "destructive_tools_blocked_by_default": True,
                },
            }
            if not call.arguments.get("include_tools", False):
                content.pop("available_tool_families", None)
            return RuntimeToolResult(
                call_id=call.id,
                name=call.name,
                status="completed",
                content=json.dumps(content, ensure_ascii=False),
                metadata={"family": "runtime", "risk": "read"},
            )

        if call.name == "bob_memory_context_summary":
            memory_context = metadata.get("memory_context") if isinstance(metadata, dict) else None
            content = _summarize_memory_context(
                memory_context=memory_context if isinstance(memory_context, dict) else {},
                max_items=_bounded_int(call.arguments.get("max_items"), default=4, minimum=1, maximum=8),
            )
            return RuntimeToolResult(
                call_id=call.id,
                name=call.name,
                status="completed",
                content=json.dumps(content, ensure_ascii=False),
                metadata={"family": "memory", "risk": "read"},
            )

        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="rejected",
            content=json.dumps({"error": "tool_not_registered", "tool": call.name}, ensure_ascii=False),
            metadata={"risk": "blocked"},
        )


def _function_tool(*, name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
            },
        },
    }


def _summarize_memory_context(*, memory_context: dict[str, Any], max_items: int) -> dict[str, Any]:
    private = memory_context.get("private") if isinstance(memory_context.get("private"), list) else []
    organization = memory_context.get("organization") if isinstance(memory_context.get("organization"), list) else []
    degraded = memory_context.get("degraded") if isinstance(memory_context.get("degraded"), list) else []
    items = []
    for scope, records in (("private", private), ("organization", organization)):
        for record in records[:max_items]:
            if not isinstance(record, dict):
                continue
            items.append(
                {
                    "scope": scope,
                    "id": record.get("id"),
                    "title": record.get("title"),
                    "memory_type": record.get("memory_type"),
                }
            )
            if len(items) >= max_items:
                break
        if len(items) >= max_items:
            break
    return {
        "items": items,
        "degraded": degraded,
        "source": memory_context.get("source") or "agent-memory-backend-api",
    }


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))
