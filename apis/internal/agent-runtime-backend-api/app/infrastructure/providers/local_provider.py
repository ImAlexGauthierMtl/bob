"""Local deterministic runtime provider for dev and CI."""

from __future__ import annotations

from typing import Any

from app.application.mcp_intent_router import infer_external_mcp_intent
from app.application.ports import RuntimeProviderPort
from app.domain import RuntimeModelResult, RuntimeToolCall


class LocalRuntimeProvider(RuntimeProviderPort):
    supports_tool_choice = False

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
            available_tools = _available_tool_names(tools)
            if _needs_mcp_gateway(prompt) and "bob_mcp_gateway" in available_tools:
                memory_capability = _infer_memory_capability(prompt)
                if memory_capability:
                    family, capability = memory_capability
                    return RuntimeModelResult(
                        content="",
                        provider="local",
                        model=self.model,
                        mode="local_runtime",
                        tool_calls=[
                            RuntimeToolCall(
                                id=f"local_tool_{family.replace('-', '_')}_{capability.split('.')[-1].replace('-', '_')}",
                                name="bob_mcp_gateway",
                                arguments={
                                    "operation": "execute_capability",
                                    "family": family,
                                    "capability": capability,
                                    "query": prompt,
                                    "limit": 5,
                                    "risk": "read",
                                },
                            )
                        ],
                        raw_metadata={"trace_id": trace_id, "phase": "tool_selection"},
                    )
                if _needs_bob_control_center_execution(prompt):
                    return RuntimeModelResult(
                        content="",
                        provider="local",
                        model=self.model,
                        mode="local_runtime",
                        tool_calls=[
                            RuntimeToolCall(
                                id=f"local_tool_bcc_{_infer_bob_control_center_capability(prompt).split('.')[-1].replace('-', '_')}",
                                name="bob_mcp_gateway",
                                arguments={
                                    "operation": "execute_capability",
                                    "family": "bob-control-center",
                                    "capability": _infer_bob_control_center_capability(prompt),
                                    "query": prompt,
                                    "limit": 10,
                                    "risk": "read",
                                },
                            )
                        ],
                        raw_metadata={"trace_id": trace_id, "phase": "tool_selection"},
                    )
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
                external_intent = infer_external_mcp_intent(prompt)
                if external_intent:
                    arguments = {
                        "operation": "execute_capability",
                        "family": external_intent.family,
                        "capability": external_intent.capability,
                        "query": prompt,
                        "limit": external_intent.limit,
                        "risk": external_intent.risk,
                    }
                    arguments.update(external_intent.arguments or {})
                    return RuntimeModelResult(
                        content="",
                        provider="local",
                        model=self.model,
                        mode="local_runtime",
                        tool_calls=[
                            RuntimeToolCall(
                                id=(
                                    f"local_tool_{external_intent.family.replace('-', '_')}_"
                                    f"{external_intent.capability.split('.')[-1].replace('-', '_')}"
                                ),
                                name="bob_mcp_gateway",
                                arguments=arguments,
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
            if "bob_runtime_status" in available_tools:
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
            if "bob_memory_context_summary" in available_tools:
                return RuntimeModelResult(
                    content="",
                    provider="local",
                    model=self.model,
                    mode="local_runtime",
                    tool_calls=[
                        RuntimeToolCall(
                            id="local_tool_memory_summary",
                            name="bob_memory_context_summary",
                            arguments={"max_items": 4},
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


def _available_tool_names(tools: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for tool in tools:
        function = tool.get("function") if isinstance(tool, dict) else None
        name = function.get("name") if isinstance(function, dict) else None
        if name:
            names.add(str(name))
    return names


def _last_user_prompt(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return " ".join(str(message.get("content") or "").split())[:180]
    return ""


def _needs_mcp_gateway(prompt: str) -> bool:
    normalized = prompt.lower()
    if _needs_bob_control_center_execution(prompt):
        return True
    return any(
        token in normalized
        for token in (
            "mcp",
            "factory",
            "croo connect",
            "croo-connect",
            "mail",
            "email",
            "courriel",
            "calendar",
            "calendrier",
            "drive",
            "onedrive",
            "sheet",
            "fichier",
            "file",
            "supabase",
            "pipedream",
            "zoho",
            "slack",
            "teams",
            "gitlab",
            "browser",
            "chrome",
            "web research",
            "recherche web",
            "skyswitch",
            "capabilit",
            "famille",
            "mémoire",
            "memoire",
            "memory",
            "playbook",
            "procédure",
            "procedure",
            "préférence",
            "preference",
            "journal",
        )
    )


def _infer_mcp_family(prompt: str) -> str:
    normalized = prompt.lower()
    for family in (
        "assistant-memory",
        "support-memory",
        "bob-control-center",
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
    if "bcc" in normalized or "control center" in normalized:
        return "bob-control-center"
    if any(token in normalized for token in ("agent", "agents", "skill", "skills", "tool", "tools")) and any(
        token in normalized
        for token in ("catalog", "catalogue", "settings", "param", "liste", "list", "crée", "cree", "create")
    ):
        return "bob-control-center"
    if "croo connect" in normalized or "connexion" in normalized and "compte" in normalized:
        return "croo-connect"
    if any(token in normalized for token in ("mail", "email", "courriel", "calendar", "calendrier")):
        return "mail-calendar"
    if any(token in normalized for token in ("drive", "onedrive", "sheet", "sheets", "fichier", "file")):
        return "workspace-files"
    if "supabase" in normalized or "pipedream" in normalized:
        return "pipedream-supabase"
    if "chrome" in normalized or "browser" in normalized or "navigateur" in normalized:
        return "browser"
    if "recherche web" in normalized or "web research" in normalized or "web search" in normalized:
        return "web-research"
    return "factory"


def _needs_bob_control_center_execution(prompt: str) -> bool:
    normalized = prompt.lower()
    if any(token in normalized for token in ("bob control center", "control center", "bcc")):
        return True
    return any(token in normalized for token in ("agent", "agents", "skill", "skills", "tool", "tools")) and any(
        token in normalized
        for token in ("catalog", "catalogue", "settings", "param", "paramètre", "parametre", "liste", "list")
    )


def _infer_bob_control_center_capability(prompt: str) -> str:
    normalized = prompt.lower()
    if any(token in normalized for token in ("skill", "skills", "competence", "compétence")):
        return "bob-control-center.skills-catalog"
    if any(token in normalized for token in ("tool", "tools", "outil", "outils")):
        return "bob-control-center.tools-catalog"
    if any(token in normalized for token in ("profile", "profiles", "profil", "profils", "taxonomy", "taxonomie")):
        return "bob-control-center.profiles-taxonomy"
    if any(token in normalized for token in ("role", "roles", "permission", "permissions", "rbac")):
        return "bob-control-center.roles-permissions"
    return "bob-control-center.agents-catalog"


def _infer_memory_capability(prompt: str) -> tuple[str, str] | None:
    normalized = prompt.lower()
    if _mentions_support_memory(normalized):
        if any(token in normalized for token in ("playbook", "procédure", "procedure", "runbook")):
            return ("support-memory", "support-memory.playbook")
        if any(token in normalized for token in ("cherche", "recherche", "search", "trouve", "find")):
            return ("support-memory", "support-memory.search")
        return ("support-memory", "support-memory.status")
    if _mentions_assistant_memory(normalized):
        if any(token in normalized for token in ("statut", "status", "état", "etat", "health")):
            return ("assistant-memory", "assistant-memory.status")
        if any(token in normalized for token in ("rappel", "readback", "liste", "list", "lis", "affiche")):
            return ("assistant-memory", "assistant-memory.readback")
        return ("assistant-memory", "assistant-memory.search")
    return None


def _mentions_support_memory(normalized: str) -> bool:
    return any(
        token in normalized
        for token in (
            "support-memory",
            "support memory",
            "mémoire support",
            "memoire support",
            "mémoire d'organisation",
            "memoire d'organisation",
            "organisation",
            "organization",
            "playbook",
            "procédure support",
            "procedure support",
            "runbook",
        )
    )


def _mentions_assistant_memory(normalized: str) -> bool:
    return any(
        token in normalized
        for token in (
            "assistant-memory",
            "assistant memory",
            "mémoire privée",
            "memoire privée",
            "mémoire privee",
            "memoire privee",
            "ma mémoire",
            "ma memoire",
            "memory",
            "préférence",
            "preference",
            "journal",
        )
    )


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
