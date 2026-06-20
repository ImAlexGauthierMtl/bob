"""Controlled local tool registry for Bob runtime."""

from __future__ import annotations

import json
from typing import Any

from app.application.runtime_catalog_defaults import MCP_TOOL_FAMILIES
from app.application.ports import RuntimeToolRegistryPort
from app.domain import InternalContext, RuntimeToolCall, RuntimeToolResult

_MCP_FAMILIES_BY_NAME = {str(family["family"]): family for family in MCP_TOOL_FAMILIES}


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
            _function_tool(
                name="bob_mcp_gateway",
                description=(
                    "Lit les familles MCP importees de croo-agentic, applique le gating de famille "
                    "et retourne les capacites autorisees. N'execute pas d'action externe irreversible."
                ),
                properties={
                    "operation": {
                        "type": "string",
                        "enum": ["list_families", "describe_family", "execute_capability"],
                        "description": "Operation gateway demandee.",
                    },
                    "family": {
                        "type": "string",
                        "enum": sorted(_MCP_FAMILIES_BY_NAME),
                        "description": "Famille MCP cible.",
                    },
                    "capability": {
                        "type": "string",
                        "description": "Capacite cible quand une execution future est demandee.",
                    },
                    "risk": {
                        "type": "string",
                        "enum": ["read", "write", "destructive"],
                        "description": "Risque de l'action demandee.",
                    },
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

        if call.name == "bob_mcp_gateway":
            return _execute_mcp_gateway(call=call, context=context)

        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="rejected",
            content=json.dumps({"error": "tool_not_registered", "tool": call.name}, ensure_ascii=False),
            metadata={"risk": "blocked"},
        )


def _execute_mcp_gateway(*, call: RuntimeToolCall, context: InternalContext) -> RuntimeToolResult:
    operation = str(call.arguments.get("operation") or "describe_family")
    family_name = str(call.arguments.get("family") or "").strip()
    risk = str(call.arguments.get("risk") or "read").strip().lower()

    if operation == "list_families":
        content = {
            "families": [
                {
                    "family": family["family"],
                    "servers": family["servers"],
                    "skill": family["skill"],
                    "capabilities": family["capabilities"],
                }
                for family in MCP_TOOL_FAMILIES
            ],
            "policy": _mcp_policy(context=context),
        }
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="completed",
            content=json.dumps(content, ensure_ascii=False),
            metadata={"family": "mcp", "risk": "read", "operation": operation},
        )

    family = _MCP_FAMILIES_BY_NAME.get(family_name)
    if not family:
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="rejected",
            content=json.dumps(
                {"error": "mcp_family_not_loaded", "family": family_name, "policy": _mcp_policy(context=context)},
                ensure_ascii=False,
            ),
            metadata={"family": "mcp", "risk": "blocked", "operation": operation},
        )

    if operation == "execute_capability" and risk != "read":
        content = {
            "status": "confirmation_required",
            "family": family["family"],
            "capability": call.arguments.get("capability"),
            "risk": risk,
            "reason": "write_or_destructive_mcp_action_requires_explicit_confirmation_and_connector_binding",
            "policy": _mcp_policy(context=context),
        }
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="requires_confirmation",
            content=json.dumps(content, ensure_ascii=False),
            metadata={"family": family["family"], "risk": risk, "operation": operation},
        )

    content = {
        "status": "ready_for_read",
        "family": family["family"],
        "servers": family["servers"],
        "skill": family["skill"],
        "capabilities": family["capabilities"],
        "loaded_for_run": True,
        "external_connector_bound": False,
        "next_gateway_step": "bind_mcp_server_adapter_for_external_execution",
        "policy": _mcp_policy(context=context),
    }
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="completed",
        content=json.dumps(content, ensure_ascii=False),
        metadata={"family": family["family"], "risk": "read", "operation": operation},
    )


def _mcp_policy(*, context: InternalContext) -> dict[str, Any]:
    return {
        "tool_gating_required": True,
        "max_normal_families": 3,
        "max_exceptional_families": 5,
        "tenant_id": context.tenant_id,
        "user_id": context.user_id,
        "permissions": list(context.permissions),
        "writes_require_confirmation": True,
        "secrets_redacted": True,
    }


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
