"""Default Bob runtime catalog seeded from Croo agentic contracts."""

from __future__ import annotations

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
        "skills": ["skill-routing", "skill-memory"],
        "tools": ["tool-runtime-status", "tool-memory-summary"],
    }
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
]

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


def default_runtime_settings(*, active_provider: str = "auto") -> dict[str, Any]:
    return {
        "providers": deepcopy(DEFAULT_PROVIDERS),
        "active_provider": active_provider,
        "agents": deepcopy(DEFAULT_AGENTS),
        "skills": deepcopy(DEFAULT_SKILLS),
        "tools": [*deepcopy(DEFAULT_RUNTIME_TOOLS), *default_mcp_tools()],
        "memory": deepcopy(DEFAULT_MEMORY),
        "mcp": {
            "local_only": True,
            "tool_gating_required": True,
            "max_normal_families": 3,
            "max_exceptional_families": 5,
            "families": deepcopy(MCP_TOOL_FAMILIES),
        },
        "source": "agent-runtime-backend-api",
    }


def default_mcp_tools() -> list[dict[str, Any]]:
    return [
        {
            "id": f"tool-mcp-{family['family']}",
            "name": family["family"],
            "family": family["family"],
            "risk": "gated",
            "status": "catalog",
            "execution": "mcp_gateway_pending",
            "description": "Famille MCP importee du contrat croo-agentic; execution active apres gating et connecteur.",
            "skill": family["skill"],
            "capabilities": family["capabilities"],
            "servers": list(family["servers"]),
        }
        for family in MCP_TOOL_FAMILIES
    ]
