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
        arguments = _infer_workspace_file_arguments(prompt)
        if any(token in normalized for token in ("sheet", "sheets", "tableur")):
            return McpIntent("workspace-files", "workspace-files.sheets-read", "read", arguments=arguments)
        if any(token in normalized for token in ("local", "fichier local", "local file")):
            return McpIntent("workspace-files", "workspace-files.local-files", "read", arguments=arguments)
        return McpIntent("workspace-files", "workspace-files.drive-onedrive-read", "read", arguments=arguments)
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
        pbx_capability = _infer_netsapiens_capability(normalized) if _has_netsapiens_pbx_context(normalized) else None
        if pbx_capability:
            return McpIntent("skyswitch", pbx_capability, _risk_for_netsapiens_capability(pbx_capability))
        telco_capability = _infer_skyswitch_telco_capability(normalized)
        if telco_capability:
            return McpIntent("skyswitch", telco_capability, _risk_for_skyswitch_telco_capability(telco_capability))
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
        pbx_capability = _infer_netsapiens_capability(normalized) if _has_netsapiens_pbx_context(normalized) else None
        if pbx_capability:
            return McpIntent("skyswitch", pbx_capability, _risk_for_netsapiens_capability(pbx_capability))
        telco_capability = _infer_skyswitch_telco_capability(normalized)
        if telco_capability:
            return McpIntent("skyswitch", telco_capability, _risk_for_skyswitch_telco_capability(telco_capability))
        if any(token in normalized for token in ("did", "dids", "number", "numéro", "numero")):
            return McpIntent("skyswitch", "skyswitch.telco-dids", "write-requested")
        if any(token in normalized for token in ("pbx", "subscriber", "user", "queue", "ivr", "voice", "netsapiens")):
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
    if any(
        token in normalized
        for token in (
            "netsapiens",
            "telco",
            "did",
            "dids",
            "e911",
            "cnam",
            "sms",
            "mms",
            "10dlc",
            "lnp",
            "port order",
            "phone number",
            "toll free",
            "pbx",
            "subscriber",
            "answering rule",
            "answering rules",
            "time frame",
            "timeframe",
            "conference bridge",
            "sip trunk",
            "voicemail",
            "call recording",
        )
    ):
        return "skyswitch"
    if "chrome" in normalized or "browser" in normalized or "navigateur" in normalized:
        return "browser"
    if "recherche web" in normalized or "web research" in normalized or "web search" in normalized:
        return "web-research"
    return "factory"


def _has_netsapiens_pbx_context(normalized: str) -> bool:
    return any(
        token in normalized
        for token in (
            "netsapiens",
            "pbx",
            "subscriber",
            "answering rule",
            "answering rules",
            "time frame",
            "timeframe",
            "conference bridge",
            "sip trunk",
            "voicemail",
            "call recording",
        )
    )


def _infer_skyswitch_telco_capability(normalized: str) -> str | None:
    if "e911" in normalized or "emergency" in normalized:
        if "validate" in normalized or "valide" in normalized:
            return "skyswitch.telco-e911-validate-e911"
        if "country" in normalized or "countries" in normalized or "pays" in normalized:
            return "skyswitch.telco-e911-list-countries"
        if "state" in normalized or "states" in normalized or "province" in normalized:
            return "skyswitch.telco-e911-list-states"
        if "delete" in normalized or "unprovision" in normalized or "remove" in normalized or "supprime" in normalized:
            return "skyswitch.telco-e911-unprovision-e911"
        if _has_write_intent(normalized) or "provision" in normalized:
            return "skyswitch.telco-e911-provision-e911"
        if "list" in normalized or "liste" in normalized:
            return "skyswitch.telco-e911-list-e911"
        return "skyswitch.telco-e911-get-e911"

    if "cnam" in normalized or "caller id" in normalized:
        outbound = any(token in normalized for token in ("outbound", "storage", "sortant"))
        if any(token in normalized for token in ("disable", "remove", "delete", "supprime")):
            return "skyswitch.telco-cnam-storage-outbound-remove-outbound-cnam" if outbound else "skyswitch.telco-cnam-deliveries-inbound-disable-cnam-delivery"
        if _has_write_intent(normalized) or "enable" in normalized or "set " in normalized:
            return "skyswitch.telco-cnam-storage-outbound-set-outbound-cnam" if outbound else "skyswitch.telco-cnam-deliveries-inbound-enable-cnam-delivery"
        return "skyswitch.telco-cnam-storage-outbound-get-outbound-cnam-details" if outbound else "skyswitch.telco-cnam-deliveries-inbound-get-cnam-delivery"

    if "anti-spam" in normalized or "antispam" in normalized:
        return "skyswitch.telco-anti-spam-deliveries-set-anti-spam-delivery" if _has_write_intent(normalized) else "skyswitch.telco-anti-spam-deliveries-get-anti-spam-delivery"

    if "mdr" in normalized:
        return "skyswitch.telco-sms-reports-list-mdrs"

    if any(token in normalized for token in ("sms", "mms", "message", "texting", "texto")):
        if "delivery status" in normalized or "mdr" in normalized or "report" in normalized:
            if "mdr" in normalized or "report" in normalized:
                return "skyswitch.telco-sms-reports-list-mdrs"
            return "skyswitch.telco-sms-reports-get-delivery-status"
        if "mms" in normalized:
            if "disable" in normalized:
                return "skyswitch.telco-sms-mms-provisioning-disable-mms"
            if "enable" in normalized or _has_write_intent(normalized):
                return "skyswitch.telco-sms-mms-provisioning-enable-mms"
            return "skyswitch.telco-sms-mms-provisioning-get-mms-status"
        if "disable" in normalized:
            return "skyswitch.telco-sms-mms-provisioning-disable-sms"
        if "enable" in normalized:
            return "skyswitch.telco-sms-mms-provisioning-enable-sms"
        if _has_draft_or_send_intent(normalized) or "send" in normalized or "envoie" in normalized:
            return "skyswitch.telco-message-sending-send-message"
        return "skyswitch.telco-sms-mms-provisioning-get-sms-status"

    if "lnp" in normalized or "port order" in normalized or "portability" in normalized or "portabilité" in normalized:
        if "validate" in normalized:
            return "skyswitch.telco-lnp-management-validate-order"
        if "check" in normalized:
            return "skyswitch.telco-lnp-management-check-phone-number-portability"
        if "create" in normalized or "crée" in normalized or "cree" in normalized:
            return "skyswitch.telco-lnp-management-create-port-order-request"
        if "update" in normalized or "modifie" in normalized:
            return "skyswitch.telco-lnp-management-update-port-order-request"
        if "delete" in normalized or "cancel" in normalized or "supprime" in normalized:
            return "skyswitch.telco-lnp-management-delete-port-order-request"
        if "status" in normalized:
            return "skyswitch.telco-lnp-management-list-order-status"
        return "skyswitch.telco-lnp-management-list-port-order-requests"

    if "10dlc" in normalized or "campaign" in normalized:
        if "price" in normalized or "pricing" in normalized or "prix" in normalized:
            return "skyswitch.telco-10dlc-calculate-pricing"
        if "brand" in normalized:
            if "create" in normalized:
                return "skyswitch.telco-10dlc-create-brand-draft"
            if "update" in normalized:
                return "skyswitch.telco-10dlc-update-brand"
            if "delete" in normalized:
                return "skyswitch.telco-10dlc-delete-brand"
            return "skyswitch.telco-10dlc-get-brand"
        if "create" in normalized:
            return "skyswitch.telco-10dlc-create-campaign-draft"
        if "update" in normalized:
            return "skyswitch.telco-10dlc-update-campaign"
        if "delete" in normalized:
            return "skyswitch.telco-10dlc-delete-campaign"
        return "skyswitch.telco-10dlc-list-campaigns"

    if any(token in normalized for token in ("did", "dids", "phone number", "numéro", "numero", "toll free")):
        if "route by ani" in normalized:
            if "delete" in normalized:
                return "skyswitch.telco-route-by-ani-delete-route-by-ani"
            return "skyswitch.telco-route-by-ani-provision-route-by-ani" if _has_write_intent(normalized) else "skyswitch.telco-route-by-ani-list-routes-by-ani"
        if "unroute" in normalized:
            return "skyswitch.telco-voice-route-unroute-phone-number"
        if "route" in normalized or "routing" in normalized:
            return "skyswitch.telco-voice-route-route-phone-number"
        if any(token in normalized for token in ("reserve", "réserve", "reserver", "réserver")) and "unreserve" not in normalized:
            return "skyswitch.telco-catalog-reservations-and-purchase-reserve-phone-number"
        if "unreserve" in normalized or "déréserve" in normalized or "dereserve" in normalized:
            return "skyswitch.telco-catalog-reservations-and-purchase-unreserve-phone-number"
        if "purchase" in normalized or "buy" in normalized or "achète" in normalized or "achete" in normalized:
            return "skyswitch.telco-catalog-reservations-and-purchase-purchase-phone-number"
        if "catalog" in normalized or "available" in normalized or "disponible" in normalized:
            return "skyswitch.telco-catalog-reservations-and-purchase-list-toll-free-numbers-catalog" if "toll free" in normalized else "skyswitch.telco-catalog-reservations-and-purchase-list-local-phone-numbers-catalog"
        if "detail" in normalized or "attribute" in normalized:
            if _has_write_intent(normalized):
                return "skyswitch.telco-phone-number-attributes-apply-phone-number-details"
            return "skyswitch.telco-phone-number-attributes-get-phone-number-details"
        if "disconnect" in normalized:
            return "skyswitch.telco-inventory-disconnect-phone-number"
        if "get" in normalized or "read" in normalized or "lis" in normalized:
            return "skyswitch.telco-inventory-get-phone-number"
        return "skyswitch.telco-inventory-list-phone-numbers"

    if "account" in normalized or "compte" in normalized:
        return "skyswitch.telco-accounts-list-sub-accounts" if "sub" in normalized else "skyswitch.telco-accounts-get-account"

    return None


def _risk_for_skyswitch_telco_capability(capability: str) -> str:
    if any(token in capability for token in ("-get-", "-list-", "-validate-", "-check-", "-calculate-")):
        return "read"
    if "unreserve-phone-number" in capability:
        return "write-requested"
    if any(
        token in capability
        for token in ("delete", "remove", "disconnect", "unprovision", "unroute", "disable", "cancel", "unassign", "detach")
    ):
        return "destructive-confirmed"
    return "write-requested"


def _infer_netsapiens_capability(normalized: str) -> str | None:
    action = _netsapiens_action_slug(normalized)
    if "answering rule" in normalized or "answering rules" in normalized:
        if "reorder" in normalized or "ordre" in normalized:
            return "skyswitch.pbx-answering-rules-reorder"
        return f"skyswitch.pbx-answering-rules-{action if action in {'read', 'create', 'update', 'delete'} else 'read'}"
    if "time range" in normalized or "timerange" in normalized:
        return "skyswitch.pbx-time-frames-create-time-range"
    if "time frame" in normalized or "timeframe" in normalized:
        return "skyswitch.pbx-time-frames-create"
    if "subscriber" in normalized or "subscribers" in normalized:
        return f"skyswitch.pbx-subscriber-{action if action in {'read', 'create', 'update', 'delete'} else 'read'}"
    if "device model" in normalized or "supported device" in normalized:
        return "skyswitch.pbx-device-list-supported-models"
    if "device" in normalized:
        return f"skyswitch.pbx-device-{action if action in {'read', 'create', 'update', 'delete'} else 'read'}"
    if "phone number" in normalized:
        return f"skyswitch.pbx-phone-number-{action if action in {'read', 'create', 'update'} else 'read'}"
    if "phone" in normalized:
        if "resync" in normalized:
            return "skyswitch.pbx-phone-resync"
        return f"skyswitch.pbx-phone-{action if action in {'read', 'create', 'update', 'delete'} else 'read'}"
    if "domain" in normalized:
        return f"skyswitch.pbx-domains-{action if action in {'read', 'create', 'update', 'delete', 'count'} else 'read'}"
    if "conference" in normalized:
        if "disconnect" in normalized:
            return "skyswitch.pbx-conference-bridges-disconnect-participants"
        return f"skyswitch.pbx-conference-bridges-{action if action in {'read', 'create', 'update'} else 'read'}"
    if "voicemail" in normalized:
        if "greeting" in normalized or "upload" in normalized:
            return "skyswitch.pbx-voicemail-upload-greeting"
        return f"skyswitch.pbx-voicemail-{action if action in {'read', 'delete'} else 'read'}"
    if "cdr" in normalized:
        return "skyswitch.pbx-cdr-read"
    if "recording setting" in normalized or "call recording setting" in normalized:
        if "enable" in normalized:
            return "skyswitch.pbx-recordings-enable-call-recording-setting"
        if "disable" in normalized:
            return "skyswitch.pbx-recordings-disable-call-recording-setting"
        return "skyswitch.pbx-recordings-get-call-recording-setting"
    if "recording" in normalized:
        return "skyswitch.pbx-recordings-read"
    if "agent" in normalized:
        if "unavailable" in normalized:
            return "skyswitch.pbx-agent-make-unavailable"
        if "available single" in normalized or "single call" in normalized:
            return "skyswitch.pbx-agent-make-available-single-call"
        if "available" in normalized:
            return "skyswitch.pbx-agent-make-available"
        return f"skyswitch.pbx-agent-{action if action in {'create'} else 'read-call-queue'}"
    if "sip trunk" in normalized or "sip trunks" in normalized:
        return f"skyswitch.pbx-sip-trunks-{action if action in {'read', 'create', 'update', 'delete', 'count'} else 'read'}"
    if "call" in normalized:
        if "transfer" in normalized:
            return "skyswitch.pbx-call-transfer-active"
        if "disconnect" in normalized:
            return "skyswitch.pbx-call-disconnect-active"
        if "hold" in normalized and "unhold" not in normalized:
            return "skyswitch.pbx-call-hold"
        if "unhold" in normalized:
            return "skyswitch.pbx-call-unhold"
        if "answer" in normalized:
            return "skyswitch.pbx-call-answer-active"
        if "reject" in normalized:
            return "skyswitch.pbx-call-reject-incoming"
        if "count" in normalized:
            return "skyswitch.pbx-call-count"
        if "report" in normalized:
            return "skyswitch.pbx-call-report-active"
        if action == "create":
            return "skyswitch.pbx-call-create"
        return "skyswitch.pbx-call-read-active"
    if "subscription" in normalized:
        if action == "delete":
            return "skyswitch.pbx-subscriptions-delete"
        return "skyswitch.pbx-subscriptions-read"
    return None


def _netsapiens_action_slug(normalized: str) -> str:
    if _has_destructive_intent(normalized) or any(token in normalized for token in ("delete", "supprime", "remove", "erase")):
        return "delete"
    if any(token in normalized for token in ("count", "combien")):
        return "count"
    if any(token in normalized for token in ("create", "crée", "cree", "add", "ajoute", "provision")):
        return "create"
    if any(token in normalized for token in ("update", "change", "modifie", "edit")):
        return "update"
    return "read"


def _risk_for_netsapiens_capability(capability: str) -> str:
    if any(token in capability for token in ("delete", "disconnect", "reject")):
        return "destructive-confirmed"
    if any(
        token in capability
        for token in (
            "create",
            "update",
            "resync",
            "reorder",
            "enable",
            "disable",
            "pause",
            "resume",
            "hold",
            "unhold",
            "call-answer-active",
            "transfer",
            "upload",
            "available",
        )
    ):
        return "write-requested"
    return "read"


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


def _infer_workspace_file_arguments(prompt: str) -> dict[str, Any]:
    args: dict[str, Any] = {}
    path = _first_regex_group(
        prompt,
        (
            r"(?:path|chemin|fichier local|local file|fichier|file)\s*[=:]?\s*([A-Za-z0-9_./-]+\.[A-Za-z0-9_-]+)",
            r"\b([A-Za-z0-9_./-]+\.(?:py|ts|html|css|md|json|yaml|yml|toml|sql|txt))\b",
        ),
    )
    if path:
        args["path"] = path.rstrip(".,;")
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
