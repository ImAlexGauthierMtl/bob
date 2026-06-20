"""Deterministic MCP intent routing shared by runtime providers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class McpIntent:
    family: str
    capability: str
    risk: str
    limit: int = 10
    arguments: dict[str, Any] | None = None


def infer_external_mcp_intent(prompt: str) -> McpIntent | None:
    write_intent = _infer_external_mcp_write_intent(prompt)
    if write_intent:
        return write_intent
    read_intent = _infer_external_mcp_read_intent(prompt)
    if read_intent:
        return read_intent
    return None


def _infer_external_mcp_read_intent(prompt: str) -> McpIntent | None:
    normalized = prompt.lower()
    family = _infer_mcp_family(prompt)
    if family in {"assistant-memory", "support-memory", "bob-control-center", "factory"}:
        return None
    if family == "slack":
        if any(token in normalized for token in ("channel", "channels", "canal", "canaux", "user", "users", "utilisateur")):
            return McpIntent("slack", "slack.channels-users", "read")
        return McpIntent("slack", "slack.messages-read-search", "read")
    if family == "teams":
        if any(token in normalized for token in ("channel", "channels", "canal", "canaux", "chat", "equipe", "équipe")):
            return McpIntent("teams", "teams.teams-channels-chats", "read")
        return McpIntent("teams", "teams.messages-read", "read")
    if family == "mail-calendar":
        if any(token in normalized for token in ("calendar", "calendrier", "availability", "disponibilit")):
            return McpIntent("mail-calendar", "mail-calendar.calendar-read-availability", "read")
        return McpIntent("mail-calendar", "mail-calendar.mail-read-search", "read")
    if family == "workspace-files":
        if any(token in normalized for token in ("sheet", "sheets", "tableur")):
            return McpIntent("workspace-files", "workspace-files.sheets-read", "read")
        if any(token in normalized for token in ("local", "fichier local", "local file")):
            return McpIntent("workspace-files", "workspace-files.local-files", "read")
        return McpIntent("workspace-files", "workspace-files.drive-onedrive-read", "read")
    if family == "pipedream-supabase":
        if "count" in normalized or "compte" in normalized:
            return McpIntent("pipedream-supabase", "pipedream-supabase.count", "read")
        if any(token in normalized for token in ("option", "introspection", "schema", "schéma")):
            return McpIntent("pipedream-supabase", "pipedream-supabase.options", "read")
        return McpIntent("pipedream-supabase", "pipedream-supabase.select", "read")
    if family == "gitlab-code":
        arguments = _infer_gitlab_arguments(prompt)
        if "file" in normalized or "fichier" in normalized:
            return McpIntent("gitlab-code", "gitlab-code.files", "read", arguments=arguments)
        if "code" in normalized or "search" in normalized or "recherche" in normalized:
            return McpIntent("gitlab-code", "gitlab-code.search-code", "read", arguments=arguments)
        if "tree" in normalized or "arborescence" in normalized:
            return McpIntent("gitlab-code", "gitlab-code.tree", "read", arguments=arguments)
        if "branch" in normalized or "branche" in normalized:
            return McpIntent("gitlab-code", "gitlab-code.branches", "read", arguments=arguments)
        return McpIntent("gitlab-code", "gitlab-code.projects", "read", arguments=arguments)
    if family == "browser":
        if any(token in normalized for token in ("screenshot", "capture")):
            return McpIntent("browser", "browser.screenshots", "read")
        if "session" in normalized or "auth" in normalized:
            return McpIntent("browser", "browser.auth-session", "read")
        return McpIntent("browser", "browser.ui-state", "read")
    if family == "web-research":
        if "source" in normalized or "citation" in normalized:
            return McpIntent("web-research", "web-research.sources-citations", "read")
        if "data" in normalized or "calcul" in normalized or "donnée" in normalized:
            return McpIntent("web-research", "web-research.data-calculations", "read")
        return McpIntent("web-research", "web-research.current-search", "read")
    if family == "zoho":
        if "catalog" in normalized or "catalogue" in normalized:
            return McpIntent("zoho", "zoho.billing-catalog", "read")
        return McpIntent("zoho", "zoho.billing-status-api", "read")
    if family == "croo-connect":
        return McpIntent("croo-connect", "croo-connect.list-supported-apps", "read")
    if family == "skyswitch":
        return McpIntent("skyswitch", "skyswitch.telco-connection", "read")
    return None


def _infer_external_mcp_write_intent(prompt: str) -> McpIntent | None:
    normalized = prompt.lower()
    family = _infer_mcp_family(prompt)
    if family in {"assistant-memory", "support-memory", "bob-control-center", "factory"}:
        return None
    if family == "slack":
        if _has_destructive_intent(normalized):
            return McpIntent("slack", "slack.message-management", "destructive-confirmed")
        if _has_draft_or_send_intent(normalized):
            return McpIntent("slack", "slack.draft-send", "draft")
    if family == "teams":
        if _has_draft_or_send_intent(normalized):
            return McpIntent("teams", "teams.draft-send", "draft")
        if _has_management_intent(normalized):
            return McpIntent("teams", "teams.management", "write-requested")
    if family == "mail-calendar":
        if any(token in normalized for token in ("calendar", "calendrier", "meeting", "rencontre", "rendez-vous", "event", "événement", "evenement")):
            if _has_destructive_intent(normalized):
                return McpIntent("mail-calendar", "mail-calendar.calendar-delete", "destructive-confirmed")
            if _has_write_intent(normalized) or _has_draft_or_send_intent(normalized):
                return McpIntent("mail-calendar", "mail-calendar.calendar-write", "write-requested")
        if _has_destructive_intent(normalized) or any(token in normalized for token in ("archive", "archiver")):
            return McpIntent("mail-calendar", "mail-calendar.mail-delete-archive", "destructive-confirmed")
        if _has_draft_or_send_intent(normalized) or any(token in normalized for token in ("répond", "repond", "reply", "forward", "transfère", "transfere")):
            return McpIntent("mail-calendar", "mail-calendar.mail-draft-send", "draft")
    if family == "workspace-files":
        if any(token in normalized for token in ("permission", "permissions", "partage", "share", "sharing", "acl", "accès", "acces")):
            return McpIntent("workspace-files", "workspace-files.sharing-permissions", "destructive-confirmed")
        if any(token in normalized for token in ("sheet", "sheets", "tableur", "spreadsheet")) and _has_write_intent(normalized):
            return McpIntent("workspace-files", "workspace-files.sheets-write", "write-requested")
    if family == "pipedream-supabase" and _has_write_intent(normalized):
        return McpIntent("pipedream-supabase", "pipedream-supabase.write-rpc", "write-requested")
    if family == "browser" and _has_browser_interaction_intent(normalized):
        return McpIntent("browser", "browser.interaction", "write-requested")
    if family == "zoho":
        if any(token in normalized for token in ("customer", "client", "subscription", "abonnement", "invoice", "facture", "payment", "paiement", "campaign", "campagne")):
            if _has_write_intent(normalized) or _has_destructive_intent(normalized):
                if any(token in normalized for token in ("subscription", "abonnement")):
                    return McpIntent("zoho", "zoho.billing-subscriptions", "write-requested")
                if any(token in normalized for token in ("invoice", "facture", "payment", "paiement")):
                    return McpIntent("zoho", "zoho.billing-invoices-payments", "write-requested")
                if any(token in normalized for token in ("campaign", "campagne")):
                    return McpIntent("zoho", "zoho.crm-campaigns", "write-requested")
                return McpIntent("zoho", "zoho.billing-customers", "write-requested")
    if family == "skyswitch" and (_has_write_intent(normalized) or _has_draft_or_send_intent(normalized)):
        if any(token in normalized for token in ("did", "dids", "number", "numéro", "numero")):
            return McpIntent("skyswitch", "skyswitch.telco-dids", "write-requested")
        if any(token in normalized for token in ("pbx", "subscriber", "user", "queue", "ivr", "voice")):
            return McpIntent("skyswitch", "skyswitch.pbx-api", "write-requested")
        return McpIntent("skyswitch", "skyswitch.telco-api", "write-requested")
    return None


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


def _infer_gitlab_arguments(prompt: str) -> dict[str, Any]:
    args: dict[str, Any] = {}
    project_id = _first_regex_group(
        prompt,
        (
            r"(?:project_id|projet|project)\s*[=:]?\s*([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+|\d+)",
            r"(?:dans|in)\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)",
        ),
    )
    path = _first_regex_group(
        prompt,
        (
            r"(?:path|chemin|fichier|file)\s*[=:]?\s*([A-Za-z0-9_./-]+\.[A-Za-z0-9_-]+)",
            r"\b([A-Za-z0-9_./-]+\.(?:py|ts|html|css|md|json|yaml|yml|toml|sql|txt))\b",
        ),
    )
    ref = _first_regex_group(prompt, (r"(?:ref|branche|branch)\s*[=:]?\s*([A-Za-z0-9_./-]+)",))
    if project_id:
        args["project_id"] = project_id.rstrip(".,;")
    if path:
        args["path"] = path.rstrip(".,;")
    if ref:
        args["ref"] = ref.rstrip(".,;")
    return args


def _first_regex_group(value: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, value, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip("'\"` ")
    return ""


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
