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
                external_write_capability = _infer_external_mcp_write_capability(prompt)
                if external_write_capability:
                    family, capability, risk = external_write_capability
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
                                    "limit": 10,
                                    "risk": risk,
                                },
                            )
                        ],
                        raw_metadata={"trace_id": trace_id, "phase": "tool_selection"},
                    )
                external_capability = _infer_external_mcp_read_capability(prompt)
                if external_capability:
                    family, capability = external_capability
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
                                    "limit": 10,
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


def _infer_external_mcp_read_capability(prompt: str) -> tuple[str, str] | None:
    normalized = prompt.lower()
    family = _infer_mcp_family(prompt)
    if family in {"assistant-memory", "support-memory", "bob-control-center", "factory"}:
        return None
    if family == "slack":
        if any(token in normalized for token in ("channel", "channels", "canal", "canaux", "user", "users", "utilisateur")):
            return ("slack", "slack.channels-users")
        return ("slack", "slack.messages-read-search")
    if family == "teams":
        if any(token in normalized for token in ("channel", "channels", "canal", "canaux", "chat", "equipe", "équipe")):
            return ("teams", "teams.teams-channels-chats")
        return ("teams", "teams.messages-read")
    if family == "mail-calendar":
        if any(token in normalized for token in ("calendar", "calendrier", "availability", "disponibilit")):
            return ("mail-calendar", "mail-calendar.calendar-read-availability")
        return ("mail-calendar", "mail-calendar.mail-read-search")
    if family == "workspace-files":
        if any(token in normalized for token in ("sheet", "sheets", "tableur")):
            return ("workspace-files", "workspace-files.sheets-read")
        if any(token in normalized for token in ("local", "fichier local", "local file")):
            return ("workspace-files", "workspace-files.local-files")
        return ("workspace-files", "workspace-files.drive-onedrive-read")
    if family == "pipedream-supabase":
        if "count" in normalized or "compte" in normalized:
            return ("pipedream-supabase", "pipedream-supabase.count")
        if any(token in normalized for token in ("option", "introspection", "schema", "schéma")):
            return ("pipedream-supabase", "pipedream-supabase.options")
        return ("pipedream-supabase", "pipedream-supabase.select")
    if family == "gitlab-code":
        if "branch" in normalized or "branche" in normalized:
            return ("gitlab-code", "gitlab-code.branches")
        if "tree" in normalized or "arborescence" in normalized:
            return ("gitlab-code", "gitlab-code.tree")
        if "file" in normalized or "fichier" in normalized:
            return ("gitlab-code", "gitlab-code.files")
        if "code" in normalized or "search" in normalized or "recherche" in normalized:
            return ("gitlab-code", "gitlab-code.search-code")
        return ("gitlab-code", "gitlab-code.projects")
    if family == "browser":
        if any(token in normalized for token in ("screenshot", "capture")):
            return ("browser", "browser.screenshots")
        if "session" in normalized or "auth" in normalized:
            return ("browser", "browser.auth-session")
        return ("browser", "browser.ui-state")
    if family == "web-research":
        if "source" in normalized or "citation" in normalized:
            return ("web-research", "web-research.sources-citations")
        if "data" in normalized or "calcul" in normalized or "donnée" in normalized:
            return ("web-research", "web-research.data-calculations")
        return ("web-research", "web-research.current-search")
    if family == "zoho":
        if "catalog" in normalized or "catalogue" in normalized:
            return ("zoho", "zoho.billing-catalog")
        return ("zoho", "zoho.billing-status-api")
    if family == "croo-connect":
        return ("croo-connect", "croo-connect.list-supported-apps")
    if family == "skyswitch":
        return ("skyswitch", "skyswitch.telco-connection")
    return None


def _infer_external_mcp_write_capability(prompt: str) -> tuple[str, str, str] | None:
    normalized = prompt.lower()
    family = _infer_mcp_family(prompt)
    if family in {"assistant-memory", "support-memory", "bob-control-center", "factory"}:
        return None
    if family == "slack":
        if _has_destructive_intent(normalized):
            return ("slack", "slack.message-management", "destructive-confirmed")
        if _has_draft_or_send_intent(normalized):
            return ("slack", "slack.draft-send", "draft")
    if family == "teams":
        if _has_draft_or_send_intent(normalized):
            return ("teams", "teams.draft-send", "draft")
        if _has_management_intent(normalized):
            return ("teams", "teams.management", "write-requested")
    if family == "mail-calendar":
        if any(token in normalized for token in ("calendar", "calendrier", "meeting", "rencontre", "rendez-vous", "event", "événement", "evenement")):
            if _has_destructive_intent(normalized):
                return ("mail-calendar", "mail-calendar.calendar-delete", "destructive-confirmed")
            if _has_write_intent(normalized) or _has_draft_or_send_intent(normalized):
                return ("mail-calendar", "mail-calendar.calendar-write", "write-requested")
        if _has_destructive_intent(normalized) or any(token in normalized for token in ("archive", "archiver")):
            return ("mail-calendar", "mail-calendar.mail-delete-archive", "destructive-confirmed")
        if _has_draft_or_send_intent(normalized) or any(token in normalized for token in ("répond", "repond", "reply", "forward", "transfère", "transfere")):
            return ("mail-calendar", "mail-calendar.mail-draft-send", "draft")
    if family == "workspace-files":
        if any(token in normalized for token in ("permission", "permissions", "partage", "share", "sharing", "acl", "accès", "acces")):
            return ("workspace-files", "workspace-files.sharing-permissions", "destructive-confirmed")
        if any(token in normalized for token in ("sheet", "sheets", "tableur", "spreadsheet")) and _has_write_intent(normalized):
            return ("workspace-files", "workspace-files.sheets-write", "write-requested")
    if family == "pipedream-supabase" and _has_write_intent(normalized):
        return ("pipedream-supabase", "pipedream-supabase.write-rpc", "write-requested")
    if family == "browser":
        if _has_browser_interaction_intent(normalized):
            return ("browser", "browser.interaction", "write-requested")
    if family == "zoho":
        if any(token in normalized for token in ("customer", "client", "subscription", "abonnement", "invoice", "facture", "payment", "paiement", "campaign", "campagne")):
            if _has_write_intent(normalized) or _has_destructive_intent(normalized):
                if any(token in normalized for token in ("subscription", "abonnement")):
                    return ("zoho", "zoho.billing-subscriptions", "write-requested")
                if any(token in normalized for token in ("invoice", "facture", "payment", "paiement")):
                    return ("zoho", "zoho.billing-invoices-payments", "write-requested")
                if any(token in normalized for token in ("campaign", "campagne")):
                    return ("zoho", "zoho.crm-campaigns", "write-requested")
                return ("zoho", "zoho.billing-customers", "write-requested")
    if family == "skyswitch" and (_has_write_intent(normalized) or _has_draft_or_send_intent(normalized)):
        if any(token in normalized for token in ("did", "dids", "number", "numéro", "numero")):
            return ("skyswitch", "skyswitch.telco-dids", "write-requested")
        if any(token in normalized for token in ("pbx", "subscriber", "user", "queue", "ivr", "voice")):
            return ("skyswitch", "skyswitch.pbx-api", "write-requested")
        return ("skyswitch", "skyswitch.telco-api", "write-requested")
    return None


def _has_draft_or_send_intent(normalized: str) -> bool:
    return any(
        token in normalized
        for token in (
            "prépare",
            "prepare",
            "brouillon",
            "draft",
            "envoie",
            "envoyer",
            "send",
            "poste",
            "post ",
            "publie",
            "publish",
            "message à",
            "message a",
            "écris",
            "ecris",
            "compose",
        )
    )


def _has_write_intent(normalized: str) -> bool:
    return _has_draft_or_send_intent(normalized) or any(
        token in normalized
        for token in (
            "crée",
            "cree",
            "create",
            "ajoute",
            "add",
            "insert",
            "update",
            "met à jour",
            "met a jour",
            "modifie",
            "modify",
            "edit",
            "upsert",
            "réserve",
            "reserve",
            "écris",
            "ecris",
            "write",
            "sauve",
            "save",
        )
    )


def _has_destructive_intent(normalized: str) -> bool:
    return any(
        token in normalized
        for token in (
            "supprime",
            "delete",
            "remove",
            "retire",
            "archive",
            "archiver",
            "cancel",
            "annule",
            "annuler",
            "épingle",
            "epingle",
            "pin ",
            "unpin",
        )
    )


def _has_management_intent(normalized: str) -> bool:
    return _has_write_intent(normalized) or _has_destructive_intent(normalized)


def _has_browser_interaction_intent(normalized: str) -> bool:
    return any(
        token in normalized
        for token in (
            "clique",
            "click",
            "remplis",
            "fill",
            "saisis",
            "type ",
            "navigue",
            "navigate",
            "ouvre",
            "open ",
            "connecte",
            "login",
            "submit",
            "soumet",
            "interagis",
            "interact",
        )
    )


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
