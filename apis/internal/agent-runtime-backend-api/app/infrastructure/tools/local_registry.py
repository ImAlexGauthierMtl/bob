"""Controlled local tool registry for Bob runtime."""

from __future__ import annotations

import json
from typing import Any

from app.application.mcp_intent_router import infer_external_mcp_intent
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
from app.infrastructure.tools.gitlab_read_adapter import GitLabReadAdapter, GitLabReadAdapterError
from app.infrastructure.tools.local_workspace_adapter import LocalWorkspaceAdapter, LocalWorkspaceAdapterError

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
_GITLAB_EXECUTABLE_CAPABILITIES = {
    "gitlab-code.projects",
    "gitlab-code.branches",
    "gitlab-code.tree",
    "gitlab-code.files",
    "gitlab-code.search-code",
    "projects",
    "branches",
    "tree",
    "files",
    "search-code",
    "gitlab-code.local-code",
    "local-code",
}
_MCP_CAPABILITY_IDS.update(_GITLAB_EXECUTABLE_CAPABILITIES)
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
    def __init__(
        self,
        *,
        factory_adapter: FactorySupabaseAdapter | None = None,
        gitlab_adapter: GitLabReadAdapter | None = None,
        local_workspace_adapter: LocalWorkspaceAdapter | None = None,
    ) -> None:
        self.factory_adapter = factory_adapter or FactorySupabaseAdapter.from_env()
        self.gitlab_adapter = gitlab_adapter or GitLabReadAdapter.from_env()
        self.local_workspace_adapter = local_workspace_adapter or LocalWorkspaceAdapter.from_env()

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
                    "Selectionne et execute une capacite MCP controlee pour Slack, Teams, mail/calendrier, "
                    "Factory, GitLab, fichiers, memoire, navigateur ou connecteurs externes. "
                    "Les lectures retournent les donnees ou le contrat disponible; les brouillons, ecritures "
                    "et actions destructives restent bloques par confirmation humaine."
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
                    "path": {
                        "type": "string",
                        "description": "Chemin de fichier ou dossier cible pour les capacites code.",
                    },
                    "ref": {
                        "type": "string",
                        "description": "Branche, tag ou SHA cible pour les capacites code.",
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
                        "enum": [
                            "read",
                            "draft",
                            "write-requested",
                            "destructive-confirmed",
                            "write",
                            "destructive",
                        ],
                        "description": (
                            "Risque de la capacite demandee. Utiliser draft pour un brouillon, "
                            "write-requested pour une ecriture et destructive-confirmed pour une action irreversible."
                        ),
                    },
                },
                required=["operation"],
            ),
        }
        allowed_tool_names = _allowed_runtime_tool_names(metadata)
        if allowed_tool_names is None:
            allowed_tool_names = set(available_tools)
        tools = [
            tool
            for name, tool in available_tools.items()
            if name in allowed_tool_names
        ]
        return _prioritize_tools_for_prompt(prompt=prompt, tools=tools)

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
                gitlab_adapter=self.gitlab_adapter,
                local_workspace_adapter=self.local_workspace_adapter,
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
    gitlab_adapter: GitLabReadAdapter,
    local_workspace_adapter: LocalWorkspaceAdapter,
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
    confirmed = bool(call.arguments.get("confirmed") is True or call.arguments.get("confirmation_id"))

    if operation == "execute_capability" and _risk_requires_confirmation(effective_risk) and not confirmed:
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
            confirmed=confirmed,
        )

    if operation == "execute_capability" and family["family"] == "gitlab-code":
        return _execute_gitlab_code_capability(
            call=call,
            context=context,
            gitlab_adapter=gitlab_adapter,
            local_workspace_adapter=local_workspace_adapter,
            capability=capability,
            risk=effective_risk,
            confirmed=confirmed,
        )

    if operation == "execute_capability" and family["family"] == "workspace-files":
        return _execute_workspace_files_capability(
            call=call,
            context=context,
            local_workspace_adapter=local_workspace_adapter,
            capability=capability,
            risk=effective_risk,
            confirmed=confirmed,
        )

    if operation == "execute_capability" and family["family"] == "assistant-memory":
        return _execute_assistant_memory_capability(
            call=call,
            context=context,
            metadata=metadata,
            capability=capability,
            risk=effective_risk,
            confirmed=confirmed,
        )

    if operation == "execute_capability" and family["family"] == "support-memory":
        return _execute_support_memory_capability(
            call=call,
            context=context,
            metadata=metadata,
            capability=capability,
            risk=effective_risk,
            confirmed=confirmed,
        )

    if operation == "execute_capability" and family["family"] == "bob-control-center":
        return _execute_bob_control_center_capability(
            call=call,
            context=context,
            metadata=metadata,
            capability=capability,
            risk=effective_risk,
            confirmed=confirmed,
        )

    if operation == "execute_capability":
        if _risk_requires_confirmation(effective_risk) and confirmed:
            return _execute_confirmed_mcp_contract(
                call=call,
                context=context,
                family=family,
                capability=capability,
                risk=effective_risk,
            )
        return _execute_external_mcp_read_contract(
            call=call,
            context=context,
            family=family,
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


def _prioritize_tools_for_prompt(*, prompt: str, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not infer_external_mcp_intent(prompt):
        return tools
    return sorted(
        tools,
        key=lambda tool: 0 if _function_tool_name(tool) == "bob_mcp_gateway" else 1,
    )


def _function_tool_name(tool: dict[str, Any]) -> str:
    function = tool.get("function") if isinstance(tool, dict) else None
    return str(function.get("name") or "") if isinstance(function, dict) else ""


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
    confirmed: bool = False,
) -> RuntimeToolResult:
    capability = _normalize_factory_capability(
        str(call.arguments.get("capability") or "requests-queues.list_queue_by_project").strip()
    )
    if risk != "read" and confirmed:
        return _confirmed_connector_pending_result(
            call=call,
            context=context,
            family_name="factory",
            capability_id=capability,
            risk=risk,
            next_gateway_step="bind_factory_write_adapter_and_readback",
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


def _execute_gitlab_code_capability(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    gitlab_adapter: GitLabReadAdapter,
    local_workspace_adapter: LocalWorkspaceAdapter,
    capability: dict[str, Any] | None,
    risk: str,
    confirmed: bool = False,
) -> RuntimeToolResult:
    capability_id = _normalize_gitlab_capability(
        str((capability or {}).get("id") or call.arguments.get("capability") or "projects").strip()
    )
    if risk != "read" and confirmed:
        return _confirmed_connector_pending_result(
            call=call,
            context=context,
            family_name="gitlab-code",
            capability_id=capability_id,
            risk=risk,
            next_gateway_step="bind_gitlab_write_adapter_after_human_approval",
        )

    if risk != "read":
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="requires_confirmation",
            content=_json_dumps(
                {
                    "status": "confirmation_required",
                    "family": "gitlab-code",
                    "capability": capability_id,
                    "risk": risk,
                    "reason": "gitlab_write_or_mutation_requires_explicit_confirmation_and_separate_write_adapter",
                    "policy": _mcp_policy(context=context),
                }
            ),
            metadata={"family": "gitlab-code", "risk": risk, "operation": "execute_capability"},
        )

    try:
        if capability_id == "local-code":
            content = _execute_local_workspace_read(
                adapter=local_workspace_adapter,
                call=call,
                default_operation="read_or_list",
            )
        elif capability_id == "projects":
            content = gitlab_adapter.list_projects(
                query=str(call.arguments.get("query") or ""),
                limit=_bounded_int(call.arguments.get("limit"), default=20, minimum=1, maximum=100),
            )
        elif capability_id == "branches":
            content = gitlab_adapter.list_branches(
                project_id=str(call.arguments.get("project_id") or ""),
                limit=_bounded_int(call.arguments.get("limit"), default=20, minimum=1, maximum=100),
            )
        elif capability_id == "tree":
            content = gitlab_adapter.list_tree(
                project_id=str(call.arguments.get("project_id") or ""),
                path=str(call.arguments.get("path") or ""),
                ref=str(call.arguments.get("ref") or ""),
                limit=_bounded_int(call.arguments.get("limit"), default=50, minimum=1, maximum=100),
            )
        elif capability_id == "files":
            content = gitlab_adapter.get_file(
                project_id=str(call.arguments.get("project_id") or ""),
                path=str(call.arguments.get("path") or ""),
                ref=str(call.arguments.get("ref") or ""),
            )
        elif capability_id == "search-code":
            content = gitlab_adapter.search_code(
                project_id=str(call.arguments.get("project_id") or ""),
                query=str(call.arguments.get("query") or ""),
                ref=str(call.arguments.get("ref") or ""),
                limit=_bounded_int(call.arguments.get("limit"), default=20, minimum=1, maximum=100),
            )
        else:
            return RuntimeToolResult(
                call_id=call.id,
                name=call.name,
                status="rejected",
                content=_json_dumps(
                    {
                        "error": "gitlab_capability_not_loaded",
                        "capability": capability_id,
                        "loaded_capabilities": ["projects", "branches", "tree", "files", "search-code", "local-code"],
                    }
                ),
                metadata={"family": "gitlab-code", "risk": "blocked", "operation": "execute_capability"},
            )
    except LocalWorkspaceAdapterError as exc:
        return _local_workspace_degraded_result(
            call=call,
            context=context,
            family_name="gitlab-code",
            capability_id=capability_id,
            error_code=exc.code,
        )
    except GitLabReadAdapterError as exc:
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="degraded",
            content=_json_dumps(
                {
                    "error": exc.code,
                    "family": "gitlab-code",
                    "capability": capability_id,
                    "external_connector_bound": False,
                    "execution_mode": "gitlab_read_adapter",
                    "policy": _mcp_policy(context=context),
                }
            ),
            metadata={"family": "gitlab-code", "risk": "read", "operation": "execute_capability"},
        )

    content["policy"] = _mcp_policy(context=context)
    content["external_connector_bound"] = True
    content["execution_mode"] = "local_workspace_adapter" if capability_id == "local-code" else "gitlab_read_adapter"
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="completed",
        content=_json_dumps(content),
        metadata={
            "family": "gitlab-code",
            "risk": "read",
            "operation": "execute_capability",
            "capability": capability_id,
            "external_connector_bound": True,
        },
    )


def _execute_workspace_files_capability(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    local_workspace_adapter: LocalWorkspaceAdapter,
    capability: dict[str, Any] | None,
    risk: str,
    confirmed: bool = False,
) -> RuntimeToolResult:
    capability_id = str((capability or {}).get("id") or call.arguments.get("capability") or "local-files")
    capability_id = capability_id.removeprefix("workspace-files.").strip()
    if risk != "read" and confirmed:
        return _confirmed_connector_pending_result(
            call=call,
            context=context,
            family_name="workspace-files",
            capability_id=capability_id,
            risk=risk,
            next_gateway_step="bind_workspace_write_adapter_after_human_approval",
        )

    if risk != "read":
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="requires_confirmation",
            content=_json_dumps(
                {
                    "status": "confirmation_required",
                    "family": "workspace-files",
                    "capability": capability_id,
                    "risk": risk,
                    "reason": "workspace_files_write_or_sharing_requires_explicit_confirmation_and_adapter_readback",
                    "policy": _mcp_policy(context=context),
                }
            ),
            metadata={"family": "workspace-files", "risk": risk, "operation": "execute_capability"},
        )

    if capability_id != "local-files":
        return _execute_external_mcp_read_contract(
            call=call,
            context=context,
            family=_MCP_FAMILIES_BY_NAME["workspace-files"],
            capability=capability,
            risk=risk,
        )

    try:
        content = _execute_local_workspace_read(
            adapter=local_workspace_adapter,
            call=call,
            default_operation="read_or_list",
        )
    except LocalWorkspaceAdapterError as exc:
        return _local_workspace_degraded_result(
            call=call,
            context=context,
            family_name="workspace-files",
            capability_id=capability_id,
            error_code=exc.code,
        )

    content["policy"] = _mcp_policy(context=context)
    content["external_connector_bound"] = True
    content["execution_mode"] = "local_workspace_adapter"
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="completed",
        content=_json_dumps(content),
        metadata={
            "family": "workspace-files",
            "risk": "read",
            "operation": "execute_capability",
            "capability": capability_id,
            "external_connector_bound": True,
        },
    )


def _execute_local_workspace_read(
    *,
    adapter: LocalWorkspaceAdapter,
    call: RuntimeToolCall,
    default_operation: str,
) -> dict[str, Any]:
    operation = str(call.arguments.get("local_operation") or call.arguments.get("file_operation") or default_operation)
    path = str(call.arguments.get("path") or "")
    query = str(call.arguments.get("query") or "")
    limit = _bounded_int(call.arguments.get("limit"), default=20, minimum=1, maximum=100)
    if operation == "search" or (query.strip() and not path.strip()):
        return adapter.search(query=query, path=path, limit=limit)
    return adapter.list_path(path=path, limit=limit)


def _local_workspace_degraded_result(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    family_name: str,
    capability_id: str,
    error_code: str,
) -> RuntimeToolResult:
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="degraded",
        content=_json_dumps(
            {
                "error": error_code,
                "family": family_name,
                "capability": capability_id,
                "external_connector_bound": False,
                "execution_mode": "local_workspace_adapter",
                "policy": _mcp_policy(context=context),
            }
        ),
        metadata={"family": family_name, "risk": "read", "operation": "execute_capability"},
    )


def _execute_assistant_memory_capability(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    metadata: dict[str, Any],
    capability: dict[str, Any] | None,
    risk: str,
    confirmed: bool = False,
) -> RuntimeToolResult:
    capability_id = str((capability or {}).get("id") or call.arguments.get("capability") or "status")
    capability_id = capability_id.removeprefix("assistant-memory.").strip()
    memory_context = metadata.get("memory_context") if isinstance(metadata, dict) else None
    memory_context = memory_context if isinstance(memory_context, dict) else {}

    if risk != "read" and confirmed:
        return _confirmed_connector_pending_result(
            call=call,
            context=context,
            family_name="assistant-memory",
            capability_id=capability_id,
            risk=risk,
            next_gateway_step="bind_agent_memory_write_adapter",
        )

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
    confirmed: bool = False,
) -> RuntimeToolResult:
    capability_id = str((capability or {}).get("id") or call.arguments.get("capability") or "status")
    capability_id = capability_id.removeprefix("support-memory.").strip()
    memory_context = metadata.get("memory_context") if isinstance(metadata, dict) else None
    memory_context = memory_context if isinstance(memory_context, dict) else {}
    if risk != "read" and confirmed:
        return _confirmed_connector_pending_result(
            call=call,
            context=context,
            family_name="support-memory",
            capability_id=capability_id,
            risk=risk,
            next_gateway_step="bind_organization_memory_write_adapter",
        )

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
    confirmed: bool = False,
) -> RuntimeToolResult:
    capability_id = str((capability or {}).get("id") or call.arguments.get("capability") or "agents-catalog")
    capability_id = capability_id.removeprefix("bob-control-center.").strip()
    runtime_catalog = metadata.get("runtime_catalog") if isinstance(metadata, dict) else None
    runtime_catalog = runtime_catalog if isinstance(runtime_catalog, dict) else {}

    if risk != "read" and confirmed:
        return _confirmed_connector_pending_result(
            call=call,
            context=context,
            family_name="bob-control-center",
            capability_id=capability_id,
            risk=risk,
            next_gateway_step="bind_settings_mutation_adapter",
        )

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


def _execute_external_mcp_read_contract(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    family: dict[str, Any],
    capability: dict[str, Any] | None,
    risk: str,
) -> RuntimeToolResult:
    family_name = str(family["family"])
    selected_capability = capability or _first_read_capability(family_name)
    if not selected_capability:
        return RuntimeToolResult(
            call_id=call.id,
            name=call.name,
            status="rejected",
            content=_json_dumps(
                {
                    "error": "mcp_read_capability_not_loaded",
                    "family": family_name,
                    "capability": call.arguments.get("capability"),
                    "policy": _mcp_policy(context=context),
                }
            ),
            metadata={"family": family_name, "risk": "blocked", "operation": "execute_capability"},
        )

    capability_id = str(selected_capability["id"])
    content = {
        "status": "connector_binding_required",
        "family": family_name,
        "capability": capability_id,
        "qualified_id": selected_capability.get("qualified_id"),
        "title": selected_capability.get("title"),
        "risk": risk,
        "source": "agent-runtime-backend-api",
        "servers": family.get("servers") or [],
        "skill": selected_capability.get("skill"),
        "capability_path": selected_capability.get("capability_path"),
        "mcp_tools": selected_capability.get("tools") or [],
        "external_connector_bound": False,
        "execution_mode": "contract_only_until_adapter_bound",
        "request": {
            "query": call.arguments.get("query") or "",
            "limit": _bounded_int(call.arguments.get("limit"), default=10, minimum=1, maximum=100),
        },
        "next_gateway_step": f"bind_{family_name.replace('-', '_')}_mcp_server_adapter",
        "policy": _mcp_policy(context=context),
    }
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="completed",
        content=_json_dumps(content),
        metadata={
            "family": family_name,
            "risk": "read",
            "operation": "execute_capability",
            "capability": capability_id,
            "external_connector_bound": False,
        },
    )


def _execute_confirmed_mcp_contract(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    family: dict[str, Any],
    capability: dict[str, Any] | None,
    risk: str,
) -> RuntimeToolResult:
    family_name = str(family["family"])
    selected_capability = capability or _first_non_read_capability(family_name)
    capability_id = str((selected_capability or {}).get("id") or call.arguments.get("capability") or "unknown")
    return _confirmed_connector_pending_result(
        call=call,
        context=context,
        family_name=family_name,
        capability_id=capability_id,
        risk=risk,
        next_gateway_step=f"bind_{family_name.replace('-', '_')}_mcp_server_adapter",
        extra={
            "qualified_id": (selected_capability or {}).get("qualified_id"),
            "title": (selected_capability or {}).get("title"),
            "servers": family.get("servers") or [],
            "skill": (selected_capability or {}).get("skill") or family.get("skill"),
            "mcp_tools": (selected_capability or {}).get("tools") or [],
            "request": {
                "query": call.arguments.get("query") or "",
                "limit": _bounded_int(call.arguments.get("limit"), default=10, minimum=1, maximum=100),
            },
        },
    )


def _confirmed_connector_pending_result(
    *,
    call: RuntimeToolCall,
    context: InternalContext,
    family_name: str,
    capability_id: str,
    risk: str,
    next_gateway_step: str,
    extra: dict[str, Any] | None = None,
) -> RuntimeToolResult:
    content = {
        "status": "confirmed_pending_connector",
        "family": family_name,
        "capability": capability_id,
        "risk": risk,
        "confirmed_by_user": context.user_id,
        "external_connector_bound": False,
        "execution_mode": "confirmed_contract_pending_adapter",
        "next_gateway_step": next_gateway_step,
        "policy": _mcp_policy(context=context),
        **(extra or {}),
    }
    return RuntimeToolResult(
        call_id=call.id,
        name=call.name,
        status="confirmed_pending_connector",
        content=_json_dumps(content),
        metadata={
            "family": family_name,
            "risk": risk,
            "operation": "execute_capability",
            "capability": capability_id,
            "external_connector_bound": False,
            "confirmed": True,
        },
    )


def _first_read_capability(family: str) -> dict[str, Any] | None:
    for item in mcp_capabilities_for_family(family):
        if str(item.get("risk") or "").strip().lower() in {"read", "readonly"}:
            return item
    return None


def _first_non_read_capability(family: str) -> dict[str, Any] | None:
    for item in mcp_capabilities_for_family(family):
        if str(item.get("risk") or "").strip().lower() not in {"read", "readonly"}:
            return item
    return None


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


def _normalize_gitlab_capability(capability: str) -> str:
    normalized = capability.removeprefix("gitlab-code.").strip()
    if normalized == "gitlab-code":
        return "projects"
    if normalized == "local-files":
        return "local-code"
    return normalized


def _json_dumps(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _function_tool(
    *,
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        parameters["required"] = required
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
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
