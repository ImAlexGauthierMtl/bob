"""Controlled local tool registry for Bob runtime."""

from __future__ import annotations

import json
from typing import Any

from app.application.runtime_catalog_defaults import (
    MCP_TOOL_FAMILIES,
    default_mcp_capabilities,
    mcp_capabilities_for_family,
)
from app.application.ports import RuntimeToolRegistryPort
from app.domain import InternalContext, RuntimeToolCall, RuntimeToolResult
from app.infrastructure.tools.factory_supabase_adapter import (
    FactorySupabaseAdapter,
    FactorySupabaseAdapterError,
)

_MCP_FAMILIES_BY_NAME = {str(family["family"]): family for family in MCP_TOOL_FAMILIES}
_MCP_CAPABILITY_IDS = {str(capability["qualified_id"]) for capability in default_mcp_capabilities()}
_MCP_CAPABILITY_IDS.update(str(capability["id"]) for capability in default_mcp_capabilities())
_FACTORY_EXECUTABLE_CAPABILITIES = {
    "requests-queues.list_requests",
    "requests-queues.list_queue_by_project",
    "requests-queues.get_request",
    "dev-validation.list_queue",
    "review.write",
}
_MCP_CAPABILITY_IDS.update(_FACTORY_EXECUTABLE_CAPABILITIES)
_CATALOG_TOOL_ALIASES = {
    "tool-runtime-status": "bob_runtime_status",
    "bob_runtime_status": "bob_runtime_status",
    "runtime-status": "bob_runtime_status",
    "tool-memory-summary": "bob_memory_context_summary",
    "bob_memory_context_summary": "bob_memory_context_summary",
    "memory-summary": "bob_memory_context_summary",
    "tool-mcp-gateway": "bob_mcp_gateway",
    "bob_mcp_gateway": "bob_mcp_gateway",
    "mcp-gateway": "bob_mcp_gateway",
}


class LocalRuntimeToolRegistry(RuntimeToolRegistryPort):
    def __init__(self, *, factory_adapter: FactorySupabaseAdapter | None = None) -> None:
        self.factory_adapter = factory_adapter or FactorySupabaseAdapter.from_env()

    def list_tools(
        self,
        *,
        prompt: str,
        context: InternalContext,
        metadata: dict[str, Any],
    ) -> list[dict[str, Any]]:
        available_tools = {
            "bob_runtime_status": _function_tool(
                name="bob_runtime_status",
                description="Retourne l'etat controle du runtime Bob, du provider actif et des familles d'outils disponibles.",
                properties={
                    "include_tools": {
                        "type": "boolean",
                        "description": "Inclure un apercu des familles d'outils disponibles.",
                    }
                },
            ),
            "bob_memory_context_summary": _function_tool(
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
            "bob_mcp_gateway": _function_tool(
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
                        "enum": sorted(_MCP_CAPABILITY_IDS),
                        "description": "Capacite cible quand une execution est demandee.",
                    },
                    "project_id": {
                        "type": "string",
                        "description": "Projet Factory cible quand applicable.",
                    },
                    "request_id": {
                        "type": "string",
                        "description": "Demande Factory cible quand applicable.",
                    },
                    "status": {
                        "type": "string",
                        "description": "Statut Factory cible, par exemple NEW ou DEV_VALIDATION.",
                    },
                    "query": {
                        "type": "string",
                        "description": "Recherche texte appliquee aux demandes Factory.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                        "description": "Nombre maximal d'elements a retourner.",
                    },
                    "offset": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Offset de pagination.",
                    },
                    "risk": {
                        "type": "string",
                        "enum": ["read", "write", "destructive"],
                        "description": "Risque de l'action demandee.",
                    },
                },
            ),
        }
        allowed_tool_names = _allowed_runtime_tool_names(metadata)
        if allowed_tool_names is None:
            allowed_tool_names = set(available_tools)
        return [
            tool
            for name, tool in available_tools.items()
            if name in allowed_tool_names
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
            return _execute_mcp_gateway(call=call, context=context, factory_adapter=self.factory_adapter)

        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="rejected",
            content=json.dumps({"error": "tool_not_registered", "tool": call.name}, ensure_ascii=False),
            metadata={"risk": "blocked"},
        )


def _execute_mcp_gateway(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    factory_adapter: FactorySupabaseAdapter,
) -> RuntimeToolResult:
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
                    "capability_count": len(mcp_capabilities_for_family(str(family["family"]))),
                    "capability_items": mcp_capabilities_for_family(str(family["family"])),
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

    if operation == "execute_capability" and family["family"] == "factory":
        return _execute_factory_capability(
            call=call,
            context=context,
            factory_adapter=factory_adapter,
            risk=risk,
        )

    content = {
        "status": "ready_for_read",
        "family": family["family"],
        "servers": family["servers"],
        "skill": family["skill"],
        "capabilities": family["capabilities"],
        "capability_count": len(mcp_capabilities_for_family(str(family["family"]))),
        "capability_items": mcp_capabilities_for_family(str(family["family"])),
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


def _allowed_runtime_tool_names(metadata: dict[str, Any]) -> set[str] | None:
    runtime_catalog = metadata.get("runtime_catalog") if isinstance(metadata, dict) else None
    selected_tools = runtime_catalog.get("tools") if isinstance(runtime_catalog, dict) else None
    if not isinstance(selected_tools, list):
        return None

    allowed: set[str] = set()
    for tool in selected_tools:
        if not isinstance(tool, dict):
            continue
        allowed.update(_catalog_tool_aliases(tool))
    return allowed


def _catalog_tool_aliases(tool: dict[str, Any]) -> set[str]:
    aliases: set[str] = set()
    for key in ("id", "name", "capability_id", "qualified_id"):
        value = tool.get(key)
        if not value:
            continue
        raw_value = str(value).strip().lower()
        normalized = _normalize_tool_identifier(raw_value)
        mapped = _CATALOG_TOOL_ALIASES.get(normalized)
        if mapped:
            aliases.add(mapped)
        if _looks_like_mcp_capability(raw_value) or _looks_like_mcp_capability(normalized):
            aliases.add("bob_mcp_gateway")

    family = _normalize_tool_identifier(str(tool.get("family") or ""))
    execution = _normalize_tool_identifier(str(tool.get("execution") or ""))
    if family in {"mcp", "factory"} or execution.startswith("mcp") or execution == "internal_gateway":
        aliases.add("bob_mcp_gateway")
    if family == "memory":
        aliases.add("bob_memory_context_summary")
    if family == "runtime":
        aliases.add("bob_runtime_status")
    return aliases


def _normalize_tool_identifier(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def _looks_like_mcp_capability(value: str) -> bool:
    if value in _MCP_CAPABILITY_IDS:
        return True
    if value.replace("-", "_") in _MCP_CAPABILITY_IDS:
        return True
    if "." in value:
        family = value.split(".", 1)[0]
        return family in _MCP_FAMILIES_BY_NAME
    return False


def _execute_factory_capability(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    factory_adapter: FactorySupabaseAdapter,
    risk: str,
) -> RuntimeToolResult:
    capability = _normalize_factory_capability(
        str(call.arguments.get("capability") or "requests-queues.list_queue_by_project").strip()
    )
    if risk != "read":
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="requires_confirmation",
            content=_json_dumps(
                {
                    "status": "confirmation_required",
                    "family": "factory",
                    "capability": capability,
                    "risk": risk,
                    "reason": "factory_write_requires_confirmed_mcp_adapter_call_and_readback",
                    "policy": _mcp_policy(context=context),
                }
            ),
            metadata={"family": "factory", "risk": risk, "operation": "execute_capability"},
        )

    try:
        if capability == "requests-queues.list_requests":
            content = factory_adapter.list_requests(
                project_id=str(call.arguments.get("project_id") or ""),
                query=str(call.arguments.get("query") or ""),
                status=str(call.arguments.get("status") or ""),
                limit=_bounded_int(call.arguments.get("limit"), default=25, minimum=1, maximum=100),
                offset=_bounded_int(call.arguments.get("offset"), default=0, minimum=0, maximum=10_000),
            )
        elif capability == "requests-queues.get_request":
            content = factory_adapter.get_request(request_id=str(call.arguments.get("request_id") or ""))
        elif capability == "dev-validation.list_queue":
            content = factory_adapter.list_requests(
                project_id=str(call.arguments.get("project_id") or ""),
                status=str(call.arguments.get("status") or "DEV_VALIDATION"),
                limit=_bounded_int(call.arguments.get("limit"), default=25, minimum=1, maximum=100),
                offset=_bounded_int(call.arguments.get("offset"), default=0, minimum=0, maximum=10_000),
            )
            content["capability"] = capability
        elif capability == "requests-queues.list_queue_by_project":
            content = factory_adapter.list_queue_by_project(
                status=str(call.arguments.get("status") or "NEW"),
                limit=_bounded_int(call.arguments.get("limit"), default=25, minimum=1, maximum=100),
                offset=_bounded_int(call.arguments.get("offset"), default=0, minimum=0, maximum=10_000),
            )
        else:
            return RuntimeToolResult(
                call_id=call.id,
                name=call.name,
                status="rejected",
                content=_json_dumps({"error": "factory_capability_not_loaded", "capability": capability}),
                metadata={"family": "factory", "risk": "blocked", "operation": "execute_capability"},
            )
    except FactorySupabaseAdapterError as exc:
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="degraded",
            content=_json_dumps(
                {
                    "error": exc.code,
                    "family": "factory",
                    "capability": capability,
                    "external_connector_bound": False,
                    "policy": _mcp_policy(context=context),
                }
            ),
            metadata={"family": "factory", "risk": "read", "operation": "execute_capability"},
        )

    content["policy"] = _mcp_policy(context=context)
    content["external_connector_bound"] = True
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="completed",
        content=_json_dumps(content),
        metadata={
            "family": "factory",
            "risk": "read",
            "operation": "execute_capability",
            "capability": capability,
        },
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


def _normalize_factory_capability(capability: str) -> str:
    normalized = capability.removeprefix("factory.").strip()
    if normalized == "requests-queues":
        return "requests-queues.list_queue_by_project"
    if normalized == "dev-validation":
        return "dev-validation.list_queue"
    return normalized


def _json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


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
