"""Default Bob runtime catalog seeded from Croo agentic contracts."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any


DEFAULT_PROVIDERS: list[dict[str, Any]] = [
    {
        "id": "fireworks-kimi",
        "name": "Fireworks Kimi K2.7 Code",
        "provider": "fireworks",
        "model": "accounts/fireworks/models/kimi-k2p7-code",
        "status": "runtime_backend_managed",
        "enabled": True,
    },
    {
        "id": "local-runtime",
        "name": "Bob Local Runtime",
        "provider": "local",
        "model": "bob-local-runtime",
        "status": "dev_fallback",
        "enabled": True,
    },
]

DEFAULT_AGENTS: list[dict[str, Any]] = [
    {
        "id": "agent-bob-orchestrator",
        "name": "Bob Orchestrator",
        "description": "Agent principal CDE pour conversation, memoire et appels outils controles.",
        "provider_id": "fireworks-kimi",
        "status": "active",
        "skills": [
            "skill-routing",
            "skill-memory",
            "skill-mcp-capability-routing",
            "skill-context-engineering",
            "skill-using-agent-skills",
            "skill-source-driven-development",
        ],
        "tools": ["tool-runtime-status", "tool-memory-summary", "tool-mcp-gateway"],
    }
]

CROO_AGENTIC_AGENT_SKILL_IMPORTS: list[tuple[str, str, str]] = [
    ("api-and-interface-design", "Api And Interface Design", "api-and-interface-design.md"),
    ("bob-le-prospecteur", "Bob Le Prospecteur", "bob-le-prospecteur.md"),
    ("browser-testing-with-devtools", "Browser Testing With Devtools", "browser-testing-with-devtools.md"),
    ("ci-cd-and-automation", "Ci Cd And Automation", "ci-cd-and-automation.md"),
    ("code-review-and-quality", "Code Review And Quality", "code-review-and-quality.md"),
    ("code-simplification", "Code Simplification", "code-simplification.md"),
    ("context-engineering", "Context Engineering", "context-engineering.md"),
    ("croo-connect-account-routing", "Croo Connect Account Routing", "croo-connect-account-routing.md"),
    ("croo-gitlab-readonly-routing", "Croo Gitlab Readonly Routing", "croo-gitlab-readonly-routing.md"),
    ("debugging-and-error-recovery", "Debugging And Error Recovery", "debugging-and-error-recovery.md"),
    ("deprecation-and-migration", "Deprecation And Migration", "deprecation-and-migration.md"),
    ("documentation-and-adrs", "Documentation And Adrs", "documentation-and-adrs.md"),
    ("doubt-driven-development", "Doubt Driven Development", "doubt-driven-development.md"),
    ("email-triage-routing", "Email Triage Routing", "email-triage-routing.md"),
    ("execute-code-research-routing", "Execute Code Research Routing", "execute-code-research-routing.md"),
    ("factory-certification-matrix", "Factory Certification Matrix", "factory-certification-matrix.md"),
    ("factory-client-validation-zoho", "Factory Client Validation Zoho", "factory-client-validation-zoho.md"),
    ("factory-cursor-cloud-fanout", "Factory Cursor Cloud Fanout", "factory-cursor-cloud-fanout.md"),
    ("factory-master-correction", "Factory Master Correction", "factory-master-correction.md"),
    ("factory-po-learning-review", "Factory Po Learning Review", "factory-po-learning-review.md"),
    ("factory-po-unit-cycle", "Factory Po Unit Cycle", "factory-po-unit-cycle.md"),
    ("factory-structure-resolution", "Factory Structure Resolution", "factory-structure-resolution.md"),
    ("factory", "Factory", "factory.md"),
    ("frontend-ui-engineering", "Frontend Ui Engineering", "frontend-ui-engineering.md"),
    ("git-workflow-and-versioning", "Git Workflow And Versioning", "git-workflow-and-versioning.md"),
    ("google-workspace-routing", "Google Workspace Routing", "google-workspace-routing.md"),
    ("idea-refine", "Idea Refine", "idea-refine.md"),
    ("incremental-implementation", "Incremental Implementation", "incremental-implementation.md"),
    ("interview-me", "Interview Me", "interview-me.md"),
    ("mcp-capability-routing", "Mcp Capability Routing", "mcp-capability-routing.md"),
    ("microsoft-365-routing", "Microsoft 365 Routing", "microsoft-365-routing.md"),
    ("observability-and-instrumentation", "Observability And Instrumentation", "observability-and-instrumentation.md"),
    ("performance-optimization", "Performance Optimization", "performance-optimization.md"),
    ("pipedream-supabase-routing", "Pipedream Supabase Routing", "pipedream-supabase-routing.md"),
    ("planning-and-task-breakdown", "Planning And Task Breakdown", "planning-and-task-breakdown.md"),
    ("prospecting-data-sources-routing", "Prospecting Data Sources Routing", "prospecting-data-sources-routing.md"),
    ("security-and-hardening", "Security And Hardening", "security-and-hardening.md"),
    ("shipping-and-launch", "Shipping And Launch", "shipping-and-launch.md"),
    ("skyswitch-netsapiens-pbx-support", "Skyswitch Netsapiens Pbx Support", "skyswitch-netsapiens-pbx-support.md"),
    ("skyswitch-telco-support", "Skyswitch Telco Support", "skyswitch-telco-support.md"),
    ("source-driven-development", "Source Driven Development", "source-driven-development.md"),
    ("spec-driven-development", "Spec Driven Development", "spec-driven-development.md"),
    ("support-client-identification", "Support Client Identification", "support-client-identification.md"),
    ("support-memory-review", "Support Memory Review", "support-memory-review.md"),
    ("support-ticket-zoho-desk", "Support Ticket Zoho Desk", "support-ticket-zoho-desk.md"),
    ("support-zoho-billing", "Support Zoho Billing", "support-zoho-billing.md"),
    ("support-zoho-books", "Support Zoho Books", "support-zoho-books.md"),
    ("support-zoho-crm", "Support Zoho Crm", "support-zoho-crm.md"),
    ("test-driven-development", "Test Driven Development", "test-driven-development.md"),
    ("using-agent-skills", "Using Agent Skills", "using-agent-skills.md"),
    ("web-search-source-policy", "Web Search Source Policy", "web-search-source-policy.md"),
]

DEFAULT_SKILLS: list[dict[str, Any]] = [
    {
        "id": "skill-routing",
        "name": "Tool Routing",
        "description": "Selectionne les familles d'outils exposees au run selon le contexte.",
        "status": "active",
        "scope": "shared_clean",
        "source": "croo-agentic/agents/assistant-local/skills/tool-skill-routing",
    },
    {
        "id": "skill-memory",
        "name": "Memory Readback",
        "description": "Resume et verifie la memoire privee et organisationnelle transmise par Bob Chat.",
        "status": "active",
        "scope": "shared_clean",
        "source": "croo-agentic/agents/assistant-local/skills/private-memory-rag",
    },
]

DEFAULT_RUNTIME_TOOLS: list[dict[str, Any]] = [
    {
        "id": "tool-runtime-status",
        "name": "bob_runtime_status",
        "family": "runtime",
        "risk": "read",
        "status": "active",
        "execution": "internal",
        "description": "Confirme l'etat runtime, les droits et les familles d'outils disponibles.",
    },
    {
        "id": "tool-memory-summary",
        "name": "bob_memory_context_summary",
        "family": "memory",
        "risk": "read",
        "status": "active",
        "execution": "internal",
        "description": "Resume le contexte memoire deja fourni au runtime.",
    },
    {
        "id": "tool-mcp-gateway",
        "name": "bob_mcp_gateway",
        "family": "mcp",
        "risk": "read",
        "status": "active",
        "execution": "internal_gateway",
        "description": "Lit le catalogue MCP croo-agentic et applique le gating de famille avant execution.",
    },
]

MCP_CAPABILITY_REGISTRY: dict[str, list[dict[str, Any]]] = {
    "assistant-memory": [
        {"id": "status", "title": "Statut memoire", "file": "status.md", "risk": "read", "tools": ["assistant_memory_status"]},
        {"id": "search", "title": "Recherche RAG privee", "file": "search.md", "risk": "read", "tools": ["assistant_memory_search"]},
        {"id": "record-memory", "title": "Ecriture memoire", "file": "record-memory.md", "risk": "write-requested", "tools": ["assistant_memory_record"]},
        {"id": "record-journal", "title": "Journal prive", "file": "record-journal.md", "risk": "write-requested", "tools": ["assistant_journal_record"]},
        {"id": "readback", "title": "Readback memoire", "file": "readback.md", "risk": "read", "tools": ["assistant_memory_readback"]},
        {"id": "promote-candidate", "title": "Promotion candidate", "file": "promote-candidate.md", "risk": "write-requested", "tools": ["assistant_memory_promote_candidate"]},
    ],
    "support-memory": [
        {"id": "status", "title": "Statut support memory", "file": "status.md", "risk": "read", "tools": ["support_memory_status"]},
        {"id": "search", "title": "Recherche memoire support", "file": "search.md", "risk": "read", "tools": ["search_support_memory"]},
        {"id": "playbook", "title": "Playbook support", "file": "playbook.md", "risk": "read", "tools": ["get_support_playbook"]},
        {"id": "propose-training", "title": "Proposer formation", "file": "propose-training.md", "risk": "draft", "tools": ["propose_training_entry"]},
        {"id": "review-pending", "title": "Revue pending", "file": "review-pending.md", "risk": "write-requested", "tools": ["list_pending_training", "review_pending_training_batch", "approve_training_entry", "reject_training_entry"]},
    ],
    "bob-control-center": [
        {"id": "agents-catalog", "title": "Catalogue agents", "file": "agents-catalog.md", "risk": "read", "tools": ["list_runtime_agents", "get_runtime_agent"]},
        {"id": "skills-catalog", "title": "Catalogue skills", "file": "skills-catalog.md", "risk": "read", "tools": ["list_runtime_skills", "get_runtime_skill"]},
        {"id": "tools-catalog", "title": "Catalogue tools", "file": "tools-catalog.md", "risk": "read", "tools": ["list_runtime_tools", "get_runtime_tool"]},
        {"id": "profiles-taxonomy", "title": "Profils et taxonomie BCC", "file": "profiles-taxonomy.md", "risk": "read", "tools": ["list_bcc_profiles", "get_bcc_profile"]},
        {"id": "roles-permissions", "title": "Roles et permissions", "file": "roles-permissions.md", "risk": "read", "tools": ["list_bcc_roles", "list_bcc_permissions"]},
        {"id": "interview-session", "title": "Entrevue profilee", "file": "interview-session.md", "risk": "draft", "tools": ["start_bcc_interview", "draft_bcc_profile_update"]},
        {"id": "library-write", "title": "Ecriture bibliotheque BCC", "file": "library-write.md", "risk": "write-requested", "tools": ["create_bcc_skill", "update_bcc_task", "link_bcc_resource"]},
    ],
    "croo-connect": [
        {"id": "list-supported-apps", "title": "Lister apps supportees", "file": "list-supported-apps.md", "risk": "read", "tools": ["list_supported_apps"]},
        {"id": "connect-account", "title": "Connecter un compte", "file": "connect-account.md", "risk": "write-requested", "tools": ["connect_account"]},
    ],
    "zoho": [
        {"id": "desk-queues-tickets", "title": "Desk queues et tickets", "file": "desk-queues-tickets.md", "risk": "write-requested", "tools": ["list_tickets", "get_ticket", "get_ticket_threads", "create_ticket"]},
        {"id": "billing-status-api", "title": "Billing statut et API", "file": "billing-status-api.md", "risk": "read", "tools": ["zoho_billing_connection_status", "zoho_billing_api_request"]},
        {"id": "billing-customers", "title": "Billing clients", "file": "billing-customers.md", "risk": "write-requested", "tools": ["zoho_billing_list_customers", "zoho_billing_create_customer", "zoho_billing_update_customer"]},
        {"id": "billing-subscriptions", "title": "Billing subscriptions", "file": "billing-subscriptions.md", "risk": "write-requested", "tools": ["zoho_billing_list_subscriptions", "zoho_billing_create_subscription", "zoho_billing_cancel_subscription"]},
        {"id": "billing-invoices-payments", "title": "Billing factures et paiements", "file": "billing-invoices-payments.md", "risk": "write-requested", "tools": ["zoho_billing_list_invoices", "zoho_billing_create_invoice", "zoho_billing_record_payment"]},
        {"id": "billing-catalog", "title": "Billing catalogue", "file": "billing-catalog.md", "risk": "read", "tools": ["items", "plans", "addons", "coupons", "credit_notes"]},
        {"id": "crm-campaigns", "title": "CRM campaigns", "file": "crm-campaigns.md", "risk": "write-requested", "tools": ["check_campaigns_auth", "list_campaigns", "add_contacts_to_campaign"]},
    ],
    "mail-calendar": [
        {"id": "mail-read-search", "title": "Lire/rechercher courriels", "file": "mail-read-search.md", "risk": "read", "tools": ["gmail", "outlook"]},
        {"id": "mail-draft-send", "title": "Brouillon/reponse/envoi", "file": "mail-draft-send.md", "risk": "draft", "tools": ["gmail", "outlook"]},
        {"id": "mail-delete-archive", "title": "Archiver/supprimer courriel", "file": "mail-delete-archive.md", "risk": "destructive-confirmed", "tools": ["gmail", "outlook"]},
        {"id": "calendar-read-availability", "title": "Lire calendrier/disponibilites", "file": "calendar-read-availability.md", "risk": "read", "tools": ["google-calendar", "outlook-calendar"]},
        {"id": "calendar-write", "title": "Ecrire calendrier", "file": "calendar-write.md", "risk": "write-requested", "tools": ["google-calendar", "outlook-calendar"]},
        {"id": "calendar-delete", "title": "Supprimer rendez-vous", "file": "calendar-delete.md", "risk": "destructive-confirmed", "tools": ["google-calendar", "outlook-calendar"]},
    ],
    "slack": [
        {"id": "channels-users", "title": "Canaux et utilisateurs", "file": "channels-users.md", "risk": "read", "tools": ["pipedream-slack"]},
        {"id": "messages-read-search", "title": "Lire/rechercher messages", "file": "messages-read-search.md", "risk": "read", "tools": ["pipedream-slack"]},
        {"id": "draft-send", "title": "Brouillon/envoi message", "file": "draft-send.md", "risk": "draft", "tools": ["pipedream-slack"]},
        {"id": "message-management", "title": "Modifier/epingler/supprimer", "file": "message-management.md", "risk": "destructive-confirmed", "tools": ["pipedream-slack"]},
    ],
    "teams": [
        {"id": "teams-channels-chats", "title": "Equipes/canaux/chats", "file": "teams-channels-chats.md", "risk": "read", "tools": ["pipedream-teams"]},
        {"id": "messages-read", "title": "Lire messages", "file": "messages-read.md", "risk": "read", "tools": ["pipedream-teams"]},
        {"id": "draft-send", "title": "Brouillon/envoi message", "file": "draft-send.md", "risk": "draft", "tools": ["pipedream-teams"]},
        {"id": "management", "title": "Gestion Teams", "file": "management.md", "risk": "write-requested", "tools": ["pipedream-teams"]},
    ],
    "workspace-files": [
        {"id": "drive-onedrive-read", "title": "Drive/OneDrive lecture", "file": "drive-onedrive-read.md", "risk": "read", "tools": ["pipedream-google-drive", "pipedream-onedrive"]},
        {"id": "sharing-permissions", "title": "Partage/permissions", "file": "sharing-permissions.md", "risk": "destructive-confirmed", "tools": ["drive", "onedrive"]},
        {"id": "sheets-read", "title": "Google Sheets lecture", "file": "sheets-read.md", "risk": "read", "tools": ["pipedream-google-sheets"]},
        {"id": "sheets-write", "title": "Google Sheets ecriture", "file": "sheets-write.md", "risk": "write-requested", "tools": ["pipedream-google-sheets"]},
        {"id": "local-files", "title": "Fichiers locaux", "file": "local-files.md", "risk": "read", "tools": ["filesystem-local"]},
    ],
    "pipedream-supabase": [
        {"id": "count", "title": "Count", "file": "count.md", "risk": "read", "tools": ["supabase-count-rows"]},
        {"id": "select", "title": "Select", "file": "select.md", "risk": "read", "tools": ["supabase-select-row"]},
        {"id": "write-rpc", "title": "Insert/update/upsert/RPC", "file": "write-rpc.md", "risk": "write-requested", "tools": ["supabase-write-tools"]},
        {"id": "options", "title": "Options/introspection", "file": "options.md", "risk": "read", "tools": ["retrieve-options", "list-options"]},
    ],
    "factory": [
        {"id": "projects-structure-repos", "title": "Projets/repos/structure", "file": "projects-structure-repos.md", "risk": "read", "tools": ["search_project", "list_projects", "get_project"]},
        {"id": "requests-queues", "title": "Demandes et queues", "file": "requests-queues.md", "risk": "read", "tools": ["list_requests", "list_queue_by_project", "get_request"]},
        {"id": "images", "title": "Images/captures", "file": "images.md", "risk": "read", "tools": ["factory_memory_analyze_image", "factory_supabase_analyze_image"]},
        {"id": "request-write-status-bug", "title": "Creer/modifier demande", "file": "request-write-status-bug.md", "risk": "write-requested", "tools": ["create_request", "update_request", "report_bug"]},
        {"id": "request-units", "title": "Unites", "file": "request-units.md", "risk": "write-requested", "tools": ["list_request_units", "record_request_unit", "update_request_unit"]},
        {"id": "cursor-plans", "title": "Cursor plans", "file": "cursor-plans.md", "risk": "write-requested", "tools": ["launch_cursor_plan", "list_cursor_plans", "apply_cursor_plan"]},
        {"id": "dev-validation", "title": "Dev validation", "file": "dev-validation.md", "risk": "write-requested", "tools": ["list_dev_validation", "record_dev_validation_review"]},
        {"id": "po-learning", "title": "PO learning", "file": "po-learning.md", "risk": "write-requested", "tools": ["search_po_learning", "propose_po_learning", "decide_po_learning"]},
        {"id": "sync-cadrage", "title": "Sync et cadrage", "file": "sync-cadrage.md", "risk": "write-requested", "tools": ["sync_supabase", "record_cadrage", "execution_units"]},
    ],
    "gitlab-code": [
        {"id": "projects", "title": "Projets", "file": "projects.md", "risk": "read", "tools": ["gitlab_get_project", "gitlab_search_projects"]},
        {"id": "branches", "title": "Branches", "file": "branches.md", "risk": "read", "tools": ["gitlab_list_branches"]},
        {"id": "tree", "title": "Arborescence", "file": "tree.md", "risk": "read", "tools": ["gitlab_list_tree"]},
        {"id": "files", "title": "Fichiers", "file": "files.md", "risk": "read", "tools": ["gitlab_get_file"]},
        {"id": "search-code", "title": "Recherche code", "file": "search-code.md", "risk": "read", "tools": ["gitlab_search_code"]},
        {"id": "local-code", "title": "Fichiers locaux", "file": "local-code.md", "risk": "read", "tools": ["filesystem-local"]},
    ],
    "browser": [
        {"id": "ui-state", "title": "Verifier etat UI", "file": "ui-state.md", "risk": "read", "tools": ["browser", "chrome"]},
        {"id": "screenshots", "title": "Captures", "file": "screenshots.md", "risk": "read", "tools": ["browser", "chrome"]},
        {"id": "interaction", "title": "Interaction", "file": "interaction.md", "risk": "write-requested", "tools": ["browser", "chrome"]},
        {"id": "auth-session", "title": "Auth/session", "file": "auth-session.md", "risk": "read", "tools": ["browser", "chrome"]},
    ],
    "web-research": [
        {"id": "current-search", "title": "Recherche actuelle", "file": "current-search.md", "risk": "read", "tools": ["web-search", "serper"]},
        {"id": "sources-citations", "title": "Sources et citations", "file": "sources-citations.md", "risk": "read", "tools": ["web-search", "serper"]},
        {"id": "data-calculations", "title": "Donnees et calculs", "file": "data-calculations.md", "risk": "read", "tools": ["web-search", "serper"]},
    ],
    "skyswitch": [
        {"id": "telco-connection", "title": "Telco connexion/statut", "file": "telco-connection.md", "risk": "read", "tools": ["connect", "status", "diagnostics", "disconnect"]},
        {"id": "telco-api", "title": "Telco API generale", "file": "telco-api.md", "risk": "write-requested", "tools": ["skyswitch_api_request", "skyswitch_activepieces_domains"]},
        {"id": "telco-dids", "title": "Telco DIDs", "file": "telco-dids.md", "risk": "write-requested", "tools": ["find_did", "reserve_did", "purchase_did", "route_did"]},
        {"id": "pbx-api", "title": "PBX statut/API", "file": "pbx-api.md", "risk": "write-requested", "tools": ["netsapiens_connection_status", "netsapiens_api_request", "netsapiens_v2_request"]},
        {"id": "pbx-users-subscribers", "title": "PBX users/subscribers", "file": "pbx-users-subscribers.md", "risk": "write-requested", "tools": ["read_subscribers", "create_subscriber", "update_subscriber"]},
        {"id": "pbx-timeframes-queues", "title": "PBX timeframes/queues", "file": "pbx-timeframes-queues.md", "risk": "write-requested", "tools": ["read_timeframes", "create_queue", "add_queue_agents"]},
        {"id": "pbx-ivr-voice", "title": "PBX IVR/voice", "file": "pbx-ivr-voice.md", "risk": "draft", "tools": ["ivr_tree", "greetings", "prompt_prep"]},
    ],
}

MCP_TOOL_FAMILIES: list[dict[str, Any]] = [
    {
        "family": "assistant-memory",
        "skill": "tools/assistant-memory/SKILL.md",
        "capabilities": "tools/assistant-memory/capabilities/index.md",
        "servers": ["assistant-memory"],
    },
    {
        "family": "support-memory",
        "skill": "tools/support-memory/SKILL.md",
        "capabilities": "tools/support-memory/capabilities/index.md",
        "servers": ["support-memory"],
    },
    {
        "family": "bob-control-center",
        "skill": "tools/bob-control-center/SKILL.md",
        "capabilities": "tools/bob-control-center/capabilities/index.md",
        "servers": ["bob-runtime-settings", "bob-control-center"],
    },
    {
        "family": "croo-connect",
        "skill": "tools/croo-connect/SKILL.md",
        "capabilities": "tools/croo-connect/capabilities/index.md",
        "servers": ["croo-connect"],
    },
    {
        "family": "zoho",
        "skill": "tools/zoho/SKILL.md",
        "capabilities": "tools/zoho/capabilities/index.md",
        "servers": [
            "zoho-desk",
            "zoho-billing",
            "pipedream-zoho-desk",
            "pipedream-zoho-crm",
            "pipedream-zoho-books",
            "pipedream-zoho-billing",
        ],
    },
    {
        "family": "mail-calendar",
        "skill": "tools/mail-calendar/SKILL.md",
        "capabilities": "tools/mail-calendar/capabilities/index.md",
        "servers": [
            "pipedream-gmail",
            "pipedream-outlook",
            "pipedream-google-calendar",
            "pipedream-outlook-calendar",
        ],
    },
    {
        "family": "slack",
        "skill": "tools/slack/SKILL.md",
        "capabilities": "tools/slack/capabilities/index.md",
        "servers": ["pipedream-slack"],
    },
    {
        "family": "teams",
        "skill": "tools/teams/SKILL.md",
        "capabilities": "tools/teams/capabilities/index.md",
        "servers": ["pipedream-teams"],
    },
    {
        "family": "workspace-files",
        "skill": "tools/workspace-files/SKILL.md",
        "capabilities": "tools/workspace-files/capabilities/index.md",
        "servers": ["pipedream-google-drive", "pipedream-google-sheets", "pipedream-onedrive"],
    },
    {
        "family": "pipedream-supabase",
        "skill": "tools/pipedream-supabase/SKILL.md",
        "capabilities": "tools/pipedream-supabase/capabilities/index.md",
        "servers": ["pipedream-supabase"],
    },
    {
        "family": "factory",
        "skill": "tools/factory/SKILL.md",
        "capabilities": "tools/factory/capabilities/index.md",
        "servers": ["factory-memory", "factory-supabase"],
    },
    {
        "family": "gitlab-code",
        "skill": "tools/gitlab-code/SKILL.md",
        "capabilities": "tools/gitlab-code/capabilities/index.md",
        "servers": ["croo-gitlab"],
    },
    {
        "family": "browser",
        "skill": "tools/browser/SKILL.md",
        "capabilities": "tools/browser/capabilities/index.md",
        "servers": ["browser", "chrome"],
    },
    {
        "family": "web-research",
        "skill": "tools/web-research/SKILL.md",
        "capabilities": "tools/web-research/capabilities/index.md",
        "servers": ["web-search", "serper"],
    },
    {
        "family": "skyswitch",
        "skill": "tools/skyswitch/SKILL.md",
        "capabilities": "tools/skyswitch/capabilities/index.md",
        "servers": ["skyswitch-support", "skyswitch-pbx-nsapi"],
    },
]

DEFAULT_MEMORY: dict[str, str] = {
    "private_user": "tenant_id + user_id obligatoire",
    "organization": "promotion humaine avant usage durable",
    "rag": "Postgres source de verite, Milvus reconstructible",
    "vector_index": "ACL revalidees apres recherche vectorielle",
}

_LOCAL_RUNTIME_CAPABILITIES = {
    "assistant-memory.status",
    "assistant-memory.search",
    "assistant-memory.readback",
    "support-memory.status",
    "support-memory.search",
    "support-memory.playbook",
    "bob-control-center.agents-catalog",
    "bob-control-center.skills-catalog",
    "bob-control-center.tools-catalog",
    "bob-control-center.profiles-taxonomy",
    "bob-control-center.roles-permissions",
}

_LOCAL_WORKSPACE_CAPABILITIES = {
    "workspace-files.local-files",
    "gitlab-code.local-code",
}

_GITLAB_READ_CAPABILITIES = {
    "gitlab-code.projects",
    "gitlab-code.branches",
    "gitlab-code.tree",
    "gitlab-code.files",
    "gitlab-code.search-code",
}

_FACTORY_READ_CAPABILITIES = {
    "factory.projects-structure-repos",
    "factory.requests-queues",
    "factory.images",
    "factory.dev-validation",
}

DEFAULT_CONVERSION_INVENTORY: dict[str, Any] = {
    "target": "bob-cde-runtime",
    "status": "in_progress",
    "active_model": "accounts/fireworks/models/kimi-k2p7-code",
    "settings_modules": [
        {
            "id": "providers",
            "label": "Providers",
            "status": "ported_active",
            "owner": "agent-runtime-backend-api",
            "controls": ["fireworks-kimi", "local-runtime"],
        },
        {
            "id": "agents",
            "label": "Agents",
            "status": "ported_active",
            "owner": "agent-runtime-backend-api",
            "controls": ["/internal/agent-runtime/v1/settings/agents"],
        },
        {
            "id": "skills",
            "label": "Skills",
            "status": "ported_active",
            "owner": "agent-runtime-backend-api",
            "controls": ["/internal/agent-runtime/v1/settings/skills", "croo-agentic/agent-skills"],
        },
        {
            "id": "tools_mcp",
            "label": "Tools MCP",
            "status": "ported_active",
            "owner": "agent-runtime-backend-api",
            "controls": ["bob_mcp_gateway", "mcp.capabilities", "mcp.families"],
        },
        {
            "id": "bob_control_center",
            "label": "Bob Control Center",
            "status": "mcp_catalog_ported_legacy_backend_active",
            "owner": "agent-runtime-backend-api",
            "controls": [
                "bob-control-center.agents-catalog",
                "bob-control-center.skills-catalog",
                "bob-control-center.tools-catalog",
                "bob-control-center.profiles-taxonomy",
            ],
        },
        {
            "id": "memory_rag_vectors",
            "label": "Memory RAG Vectors",
            "status": "ported_active",
            "owner": "agent-memory-backend-api",
            "controls": ["private_user", "organization", "rag", "vector_index"],
        },
        {
            "id": "rbac_entitlements",
            "label": "RBAC Entitlements",
            "status": "platform_contract_active",
            "owner": "platform-b4f-api",
            "controls": ["bob_chat.use", "local_super_admin", "bob-cloud-contract"],
        },
    ],
    "surfaces": [
        {
            "id": "conversation",
            "label": "Conversation Bob",
            "status": "ported_active",
            "current": "bob-chat-b4f-api -> agent-runtime-backend-api",
            "target": "bob-chat-b4f-api -> agent-runtime-backend-api",
            "evidence": ["POST /api/bob-chat/v1/messages", "POST /internal/agent-runtime/v1/runs"],
        },
        {
            "id": "runtime_settings",
            "label": "Runtime Settings",
            "status": "ported_active",
            "current": "platform-b4f-api -> agent-runtime-backend-api",
            "target": "platform-b4f-api -> agent-runtime-backend-api",
            "evidence": [
                "GET /api/bob-settings/v1/runtime",
                "POST /api/bob-settings/v1/runtime/agents",
                "POST /api/bob-settings/v1/runtime/skills",
                "POST /api/bob-settings/v1/runtime/tools",
            ],
        },
        {
            "id": "bob_control_center",
            "label": "Bob Control Center",
            "status": "mcp_catalog_ported_legacy_backend_active",
            "current": "bob-control-center MCP catalog in runtime; legacy CRUD still agent-control-b4f-api -> agent-backend-api",
            "target": "bob-settings runtime + MCP governed catalog",
            "remaining_work": [
                "migrate BCC organization, role, profile and library CRUD into Bob settings modules",
                "retire agent-control public gateway after parity tests",
            ],
        },
        {
            "id": "legacy_graph_runtime",
            "label": "Legacy Graph Runtime",
            "status": "removed_from_cde_runtime",
            "current": "not present in CDE runtime search",
            "target": "no legacy graph runtime dependency",
            "evidence": ["runtime imports and settings use Bob runtime providers only"],
        },
    ],
}


def default_runtime_settings(*, active_provider: str = "auto") -> dict[str, Any]:
    return {
        "providers": deepcopy(DEFAULT_PROVIDERS),
        "active_provider": active_provider,
        "agents": deepcopy(DEFAULT_AGENTS),
        "skills": [*deepcopy(DEFAULT_SKILLS), *default_agent_skills()],
        "tools": [*deepcopy(DEFAULT_RUNTIME_TOOLS), *default_mcp_tools(), *default_mcp_capability_tools()],
        "memory": deepcopy(DEFAULT_MEMORY),
        "mcp": {
            "local_only": True,
            "tool_gating_required": True,
            "max_normal_families": 3,
            "max_exceptional_families": 5,
            "families": default_mcp_families(),
            "capabilities": default_mcp_capabilities(),
        },
        "conversion_inventory": deepcopy(DEFAULT_CONVERSION_INVENTORY),
        "source": "agent-runtime-backend-api",
    }


def default_agent_skills() -> list[dict[str, Any]]:
    return [
        {
            "id": f"skill-{slug}",
            "name": title,
            "description": f"Skill Bob importe du catalogue agentique Croo: {title}.",
            "status": "catalog",
            "scope": "agent_skill",
            "source": f"croo-agentic/agent-skills/{filename}",
        }
        for slug, title, filename in CROO_AGENTIC_AGENT_SKILL_IMPORTS
    ]


def default_mcp_families() -> list[dict[str, Any]]:
    families = deepcopy(MCP_TOOL_FAMILIES)
    for family in families:
        capability_items = mcp_capabilities_for_family(str(family["family"]))
        family["capability_count"] = len(capability_items)
        family["capability_items"] = capability_items
        family["runtime_status"] = _family_runtime_status(capability_items)
        family["active_capability_count"] = sum(
            1
            for capability in capability_items
            if _capability_counts_as_active(str(capability.get("runtime_status") or ""))
        )
    return families


def default_mcp_capabilities() -> list[dict[str, Any]]:
    return [
        _qualified_capability(family=family, capability=capability)
        for family, capabilities in MCP_CAPABILITY_REGISTRY.items()
        for capability in capabilities
    ]


def mcp_capabilities_for_family(family: str) -> list[dict[str, Any]]:
    return [
        _qualified_capability(family=family, capability=capability)
        for capability in MCP_CAPABILITY_REGISTRY.get(family, [])
    ]


def default_mcp_tools() -> list[dict[str, Any]]:
    return [
        {
            "id": f"tool-mcp-{family['family']}",
            "name": family["family"],
            "family": family["family"],
            "risk": "gated",
            "status": "catalog",
            "execution": "mcp_gateway_catalog",
            "description": "Famille MCP importee du contrat croo-agentic; lecture active via bob_mcp_gateway, actions externes gatees.",
            "skill": family["skill"],
            "capabilities": family["capabilities"],
            "servers": list(family["servers"]),
        }
        for family in MCP_TOOL_FAMILIES
    ]


def default_mcp_capability_tools() -> list[dict[str, Any]]:
    return [
        {
            "id": f"tool-mcp-{capability['family']}-{capability['id']}",
            "name": capability["qualified_id"],
            "family": capability["family"],
            "risk": capability["risk"],
            "status": "catalog",
            "execution": "mcp_gateway_capability",
            "description": capability["title"],
            "skill": capability["skill"],
            "capabilities": capability["capability_path"],
            "capability_id": capability["id"],
            "capability_file": capability["file"],
            "mcp_tools": capability["tools"],
        }
        for capability in default_mcp_capabilities()
    ]


def _qualified_capability(*, family: str, capability: dict[str, Any]) -> dict[str, Any]:
    skill = f"tools/{family}/SKILL.md"
    capability_path = f"tools/{family}/capabilities/{capability['file']}"
    qualified_id = f"{family}.{capability['id']}"
    runtime_status = _capability_runtime_status(qualified_id=qualified_id, risk=str(capability.get("risk") or "read"))
    return {
        **deepcopy(capability),
        "family": family,
        "qualified_id": qualified_id,
        "skill": skill,
        "capability_path": capability_path,
        **runtime_status,
    }


def _capability_runtime_status(*, qualified_id: str, risk: str) -> dict[str, Any]:
    normalized_risk = risk.strip().lower()
    if qualified_id in _LOCAL_RUNTIME_CAPABILITIES:
        return {
            "runtime_status": "local_runtime_active",
            "connector_status": "runtime_managed",
            "settings_status": "visible_in_settings",
        }
    if qualified_id in _LOCAL_WORKSPACE_CAPABILITIES:
        enabled = _env_enabled("BOB_LOCAL_WORKSPACE_ENABLED")
        return {
            "runtime_status": "local_adapter_active" if enabled else "local_adapter_disabled",
            "connector_status": "configured" if enabled else "disabled",
            "settings_status": "visible_in_settings",
            "remaining_work": [] if enabled else ["enable BOB_LOCAL_WORKSPACE_ENABLED"],
        }
    if qualified_id in _GITLAB_READ_CAPABILITIES:
        configured = bool(
            os.environ.get("CROO_GITLAB_TOKEN")
            or os.environ.get("GITLAB_TOKEN")
            or os.environ.get("GLAB_TOKEN")
        )
        return {
            "runtime_status": "remote_adapter_configured" if configured else "remote_adapter_missing_secret",
            "connector_status": "configured" if configured else "missing_secret",
            "settings_status": "visible_in_settings",
            "remaining_work": [] if configured else ["configure CROO_GITLAB_TOKEN"],
        }
    if qualified_id in _FACTORY_READ_CAPABILITIES:
        configured = bool(os.environ.get("FACTORY_SUPABASE_DB_URL") or os.environ.get("SUPABASE_DB_URL"))
        return {
            "runtime_status": "remote_adapter_configured" if configured else "remote_adapter_missing_secret",
            "connector_status": "configured" if configured else "missing_secret",
            "settings_status": "visible_in_settings",
            "remaining_work": [] if configured else ["configure FACTORY_SUPABASE_DB_URL or SUPABASE_DB_URL"],
        }
    if normalized_risk not in {"read", "readonly"}:
        return {
            "runtime_status": "confirmation_gated_contract",
            "connector_status": "requires_human_confirmation",
            "settings_status": "visible_in_settings",
            "remaining_work": ["bind external MCP adapter before execution"],
        }
    return {
        "runtime_status": "contract_pending_adapter",
        "connector_status": "not_bound",
        "settings_status": "visible_in_settings",
        "remaining_work": ["bind external MCP adapter"],
    }


def _family_runtime_status(capabilities: list[dict[str, Any]]) -> str:
    statuses = {str(capability.get("runtime_status") or "") for capability in capabilities}
    if statuses and all(_capability_counts_as_active(status) for status in statuses):
        return "local_active"
    if any(_capability_counts_as_active(status) for status in statuses):
        return "partially_active"
    if any(status == "remote_adapter_missing_secret" for status in statuses):
        return "needs_configuration"
    return "contract_pending"


def _capability_counts_as_active(status: str) -> bool:
    return status.endswith("_active") or status == "remote_adapter_configured"


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}
