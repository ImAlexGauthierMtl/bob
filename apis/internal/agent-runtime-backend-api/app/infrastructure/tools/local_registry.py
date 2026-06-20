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
        allowed_tool_names = _allowed_runtime_tool_names(metadata)
        if allowed_tool_names is not None and call.name not in allowed_tool_names:
            return RuntimeToolResult(
                call_id=call.id,
                name=call.name,
                status="rejected",
                content=json.dumps(
                    {"error": "tool_not_allowed_for_selected_agent", "tool": call.name},
                    ensure_ascii=False,
                ),
                metadata={"risk": "blocked"},
            )

        if call.name == "bob_runtime_status":
            content = {
                "runtime": "bob-agent-runtime",
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "permissions": list(context.permissions),
                "available_tool_families": [
                    "runtime",
                    "memory",
                    "bob-control-center",
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
            return _execute_mcp_gateway(
                call=call,
                context=context,
                metadata=metadata,
                factory_adapter=self.factory_adapter,
            )

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
    metadata: dict[str, Any],
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

    capability = _find_mcp_capability(
        family=str(family["family"]),
        capability=str(call.arguments.get("capability") or "").strip(),
    )
    effective_risk = _effective_capability_risk(call_risk=risk, capability=capability)

    if operation == "execute_capability" and _risk_requires_confirmation(effective_risk):
        content = {
            "status": "confirmation_required",
            "family": family["family"],
            "capability": call.arguments.get("capability"),
            "risk": effective_risk,
            "reason": "write_or_destructive_mcp_action_requires_explicit_confirmation_and_connector_binding",
            "policy": _mcp_policy(context=context),
        }
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="requires_confirmation",
            content=json.dumps(content, ensure_ascii=False),
            metadata={"family": family["family"], "risk": effective_risk, "operation": operation},
        )

    if operation == "execute_capability" and family["family"] == "factory":
        return _execute_factory_capability(
            call=call,
            context=context,
            factory_adapter=factory_adapter,
            risk=effective_risk,
        )

    if operation == "execute_capability" and family["family"] == "assistant-memory":
        return _execute_assistant_memory_capability(
            call=call,
            context=context,
            metadata=metadata,
            capability=capability,
            risk=effective_risk,
        )

    if operation == "execute_capability" and family["family"] == "support-memory":
        return _execute_support_memory_capability(
            call=call,
            context=context,
            metadata=metadata,
            capability=capability,
            risk=effective_risk,
        )

    if operation == "execute_capability" and family["family"] == "bob-control-center":
        return _execute_bob_control_center_capability(
            call=call,
            context=context,
            metadata=metadata,
            capability=capability,
            risk=effective_risk,
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
    if family in {"mcp", "factory", "bob-control-center"} or execution.startswith("mcp") or execution == "internal_gateway":
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


def _find_mcp_capability(*, family: str, capability: str) -> dict[str, Any] | None:
    normalized = capability.removeprefix(f"{family}.").strip()
    for item in mcp_capabilities_for_family(family):
        if capability in {str(item["qualified_id"]), str(item["id"])}:
            return item
        if normalized in {str(item["id"]), str(item["qualified_id"])}:
            return item
    return None


def _effective_capability_risk(*, call_risk: str, capability: dict[str, Any] | None) -> str:
    capability_risk = str((capability or {}).get("risk") or "").strip().lower()
    if capability_risk:
        return capability_risk
    return call_risk or "read"


def _risk_requires_confirmation(risk: str) -> bool:
    return risk not in {"read", "readonly"}


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


def _execute_assistant_memory_capability(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    metadata: dict[str, Any],
    capability: dict[str, Any] | None,
    risk: str,
) -> RuntimeToolResult:
    capability_id = str((capability or {}).get("id") or call.arguments.get("capability") or "status")
    capability_id = capability_id.removeprefix("assistant-memory.").strip()
    memory_context = metadata.get("memory_context") if isinstance(metadata, dict) else None
    memory_context = memory_context if isinstance(memory_context, dict) else {}

    if risk != "read":
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="requires_confirmation",
            content=_json_dumps(
                {
                    "status": "confirmation_required",
                    "family": "assistant-memory",
                    "capability": capability_id,
                    "risk": risk,
                    "reason": "assistant_memory_write_requires_explicit_confirmation",
                    "policy": _mcp_policy(context=context),
                }
            ),
            metadata={"family": "assistant-memory", "risk": risk, "operation": "execute_capability"},
        )

    if capability_id == "status":
        content = _assistant_memory_status(memory_context=memory_context)
    elif capability_id == "search":
        content = _assistant_memory_search(
            memory_context=memory_context,
            query=str(call.arguments.get("query") or ""),
            max_items=_bounded_int(call.arguments.get("limit"), default=5, minimum=1, maximum=20),
        )
    elif capability_id == "readback":
        content = _assistant_memory_readback(
            memory_context=memory_context,
            max_items=_bounded_int(call.arguments.get("limit"), default=6, minimum=1, maximum=20),
        )
    else:
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="rejected",
            content=_json_dumps(
                {
                    "error": "assistant_memory_capability_not_loaded",
                    "capability": capability_id,
                    "loaded_capabilities": ["status", "search", "readback"],
                }
            ),
            metadata={"family": "assistant-memory", "risk": "blocked", "operation": "execute_capability"},
        )

    content["policy"] = _mcp_policy(context=context)
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="completed",
        content=_json_dumps(content),
        metadata={
            "family": "assistant-memory",
            "risk": "read",
            "operation": "execute_capability",
            "capability": capability_id,
        },
    )


def _execute_support_memory_capability(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    metadata: dict[str, Any],
    capability: dict[str, Any] | None,
    risk: str,
) -> RuntimeToolResult:
    capability_id = str((capability or {}).get("id") or call.arguments.get("capability") or "status")
    capability_id = capability_id.removeprefix("support-memory.").strip()
    memory_context = metadata.get("memory_context") if isinstance(metadata, dict) else None
    memory_context = memory_context if isinstance(memory_context, dict) else {}

    if capability_id == "status":
        content = _support_memory_status(memory_context=memory_context)
    elif capability_id == "search":
        content = _support_memory_search(
            memory_context=memory_context,
            query=str(call.arguments.get("query") or ""),
            max_items=_bounded_int(call.arguments.get("limit"), default=5, minimum=1, maximum=20),
        )
    elif capability_id == "playbook":
        content = _support_memory_playbook(
            memory_context=memory_context,
            query=str(call.arguments.get("query") or ""),
            max_items=_bounded_int(call.arguments.get("limit"), default=5, minimum=1, maximum=20),
        )
    else:
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="rejected",
            content=_json_dumps(
                {
                    "error": "support_memory_capability_not_loaded",
                    "capability": capability_id,
                    "loaded_capabilities": ["status", "search", "playbook"],
                }
            ),
            metadata={"family": "support-memory", "risk": "blocked", "operation": "execute_capability"},
        )

    content["policy"] = _mcp_policy(context=context)
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="completed",
        content=_json_dumps(content),
        metadata={
            "family": "support-memory",
            "risk": risk,
            "operation": "execute_capability",
            "capability": capability_id,
        },
    )


def _execute_bob_control_center_capability(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    metadata: dict[str, Any],
    capability: dict[str, Any] | None,
    risk: str,
) -> RuntimeToolResult:
    capability_id = str((capability or {}).get("id") or call.arguments.get("capability") or "agents-catalog")
    capability_id = capability_id.removeprefix("bob-control-center.").strip()
    runtime_catalog = metadata.get("runtime_catalog") if isinstance(metadata, dict) else None
    runtime_catalog = runtime_catalog if isinstance(runtime_catalog, dict) else {}

    if risk != "read":
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="requires_confirmation",
            content=_json_dumps(
                {
                    "status": "confirmation_required",
                    "family": "bob-control-center",
                    "capability": capability_id,
                    "risk": risk,
                    "reason": "bob_control_center_write_requires_settings_mutation_or_confirmed_mcp_adapter",
                    "policy": _mcp_policy(context=context),
                }
            ),
            metadata={"family": "bob-control-center", "risk": risk, "operation": "execute_capability"},
        )

    if capability_id in {"agents-catalog", "skills-catalog", "tools-catalog"}:
        content = _bob_control_center_runtime_catalog(
            runtime_catalog=runtime_catalog,
            capability_id=capability_id,
        )
    elif capability_id in {"profiles-taxonomy", "roles-permissions"}:
        content = _bob_control_center_legacy_contract(capability_id=capability_id)
    else:
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="rejected",
            content=_json_dumps(
                {
                    "error": "bob_control_center_capability_not_loaded",
                    "capability": capability_id,
                    "loaded_capabilities": [
                        "agents-catalog",
                        "skills-catalog",
                        "tools-catalog",
                        "profiles-taxonomy",
                        "roles-permissions",
                    ],
                }
            ),
            metadata={"family": "bob-control-center", "risk": "blocked", "operation": "execute_capability"},
        )

    content["policy"] = _mcp_policy(context=context)
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="completed",
        content=_json_dumps(content),
        metadata={
            "family": "bob-control-center",
            "risk": "read",
            "operation": "execute_capability",
            "capability": capability_id,
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


def _assistant_memory_status(*, memory_context: dict[str, Any]) -> dict[str, Any]:
    private = memory_context.get("private") if isinstance(memory_context.get("private"), list) else []
    organization = memory_context.get("organization") if isinstance(memory_context.get("organization"), list) else []
    degraded = memory_context.get("degraded") if isinstance(memory_context.get("degraded"), list) else []
    return {
        "status": "available",
        "family": "assistant-memory",
        "source": memory_context.get("source") or "agent-memory-backend-api",
        "private_count": len(private),
        "organization_count": len(organization),
        "degraded": degraded[:5],
        "read_capabilities": ["status", "search", "readback"],
        "write_capabilities_require_confirmation": ["record-memory", "record-journal", "promote-candidate"],
    }


def _assistant_memory_readback(*, memory_context: dict[str, Any], max_items: int) -> dict[str, Any]:
    return {
        "status": "completed",
        "family": "assistant-memory",
        "source": memory_context.get("source") or "agent-memory-backend-api",
        "items": _memory_items(memory_context=memory_context, max_items=max_items),
    }


def _assistant_memory_search(*, memory_context: dict[str, Any], query: str, max_items: int) -> dict[str, Any]:
    normalized_query = " ".join(query.lower().split())
    candidates = _memory_items(memory_context=memory_context, max_items=100)
    if normalized_query:
        matches = [
            item
            for item in candidates
            if normalized_query in _memory_item_search_text(item)
        ]
    else:
        matches = candidates
    return {
        "status": "completed",
        "family": "assistant-memory",
        "source": memory_context.get("source") or "agent-memory-backend-api",
        "query": query,
        "total_matching": len(matches),
        "items": matches[:max_items],
    }


def _memory_items(*, memory_context: dict[str, Any], max_items: int) -> list[dict[str, Any]]:
    private = memory_context.get("private") if isinstance(memory_context.get("private"), list) else []
    organization = memory_context.get("organization") if isinstance(memory_context.get("organization"), list) else []
    items: list[dict[str, Any]] = []
    for scope, records in (("private", private), ("organization", organization)):
        for record in records:
            if not isinstance(record, dict):
                continue
            items.append(
                {
                    "scope": scope,
                    "id": record.get("id"),
                    "title": record.get("title"),
                    "memory_type": record.get("memory_type"),
                    "summary": record.get("summary") or record.get("content") or record.get("text"),
                    "source": record.get("source"),
                }
            )
            if len(items) >= max_items:
                return items
    return items


def _memory_item_search_text(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(field) or "").lower()
        for field in ("id", "title", "memory_type", "summary", "source", "scope")
    )


def _support_memory_status(*, memory_context: dict[str, Any]) -> dict[str, Any]:
    organization = memory_context.get("organization") if isinstance(memory_context.get("organization"), list) else []
    degraded = memory_context.get("degraded") if isinstance(memory_context.get("degraded"), list) else []
    playbooks = [
        record
        for record in organization
        if isinstance(record, dict)
        and str(record.get("memory_type") or "").lower() in {"playbook", "procedure", "runbook"}
    ]
    return {
        "status": "available",
        "family": "support-memory",
        "source": memory_context.get("source") or "agent-memory-backend-api",
        "organization_count": len(organization),
        "playbook_count": len(playbooks),
        "degraded": degraded[:5],
        "read_capabilities": ["status", "search", "playbook"],
        "write_capabilities_require_confirmation": ["propose-training", "review-pending"],
    }


def _support_memory_search(*, memory_context: dict[str, Any], query: str, max_items: int) -> dict[str, Any]:
    normalized_query = " ".join(query.lower().split())
    candidates = _organization_memory_items(memory_context=memory_context, max_items=100)
    matches = [
        item
        for item in candidates
        if not normalized_query or normalized_query in _memory_item_search_text(item)
    ]
    return {
        "status": "completed",
        "family": "support-memory",
        "source": memory_context.get("source") or "agent-memory-backend-api",
        "query": query,
        "total_matching": len(matches),
        "items": matches[:max_items],
    }


def _support_memory_playbook(*, memory_context: dict[str, Any], query: str, max_items: int) -> dict[str, Any]:
    normalized_query = " ".join(query.lower().split())
    playbooks = [
        item
        for item in _organization_memory_items(memory_context=memory_context, max_items=100)
        if str(item.get("memory_type") or "").lower() in {"playbook", "procedure", "runbook"}
    ]
    matches = [
        item
        for item in playbooks
        if not normalized_query or normalized_query in _memory_item_search_text(item)
    ]
    return {
        "status": "completed",
        "family": "support-memory",
        "source": memory_context.get("source") or "agent-memory-backend-api",
        "query": query,
        "total_matching": len(matches),
        "items": matches[:max_items],
    }


def _organization_memory_items(*, memory_context: dict[str, Any], max_items: int) -> list[dict[str, Any]]:
    organization = memory_context.get("organization") if isinstance(memory_context.get("organization"), list) else []
    scoped_context = {"private": [], "organization": organization}
    return _memory_items(memory_context=scoped_context, max_items=max_items)


def _bob_control_center_runtime_catalog(
    *,
    runtime_catalog: dict[str, Any],
    capability_id: str,
) -> dict[str, Any]:
    selected_agent = runtime_catalog.get("agent") if isinstance(runtime_catalog.get("agent"), dict) else {}
    selected_skills = runtime_catalog.get("skills") if isinstance(runtime_catalog.get("skills"), list) else []
    selected_tools = runtime_catalog.get("tools") if isinstance(runtime_catalog.get("tools"), list) else []
    return {
        "status": "completed",
        "family": "bob-control-center",
        "capability": capability_id,
        "source": "agent-runtime-backend-api",
        "runtime_settings_routes": [
            "/internal/agent-runtime/v1/settings/agents",
            "/internal/agent-runtime/v1/settings/skills",
            "/internal/agent-runtime/v1/settings/tools",
        ],
        "selected_agent": {
            "id": selected_agent.get("id"),
            "name": selected_agent.get("name"),
            "status": selected_agent.get("status"),
            "provider_id": selected_agent.get("provider_id"),
        },
        "selected_skill_count": len(selected_skills),
        "selected_tool_count": len(selected_tools),
        "selected_skills": [
            {"id": item.get("id"), "name": item.get("name"), "source": item.get("source")}
            for item in selected_skills
            if isinstance(item, dict)
        ],
        "selected_tools": [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "family": item.get("family"),
                "execution": item.get("execution"),
            }
            for item in selected_tools
            if isinstance(item, dict)
        ],
        "legacy_backend_active": True,
        "legacy_backend_boundary": "agent-control-b4f-api owns remaining BCC CRUD until migrated behind Bob settings/MCP adapters",
    }


def _bob_control_center_legacy_contract(*, capability_id: str) -> dict[str, Any]:
    return {
        "status": "ready_for_migration",
        "family": "bob-control-center",
        "capability": capability_id,
        "source": "agent-runtime-backend-api",
        "legacy_backend_active": True,
        "target_owner": "bob-settings runtime + MCP governed catalog",
        "read_contract": [
            "tenant_scoped_profile_taxonomy",
            "role_and_permission_catalog",
            "agent_skill_tool_assignments",
        ],
        "write_contract": "settings mutation or confirmed MCP adapter required",
        "next_gateway_step": "bind BCC repositories behind runtime settings adapters and retire public agent-control surface after parity tests",
    }


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))
