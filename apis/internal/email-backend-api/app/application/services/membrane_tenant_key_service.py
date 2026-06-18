"""Integration external user scoping helpers."""

from typing import Optional


_SCOPE_PER_ORG = {
    "hubspot",
    "salesforce",
    "pipedrive",
    "zoho-crm",
    "dynamics-crm",
    "attio",
    "monday",
    "jira",
    "confluence",
}


def build_tenant_key(tenant_id: str, scope: str, user_id: str, org_id: Optional[str]) -> str:
    """Build a namespaced external user key for provider integrations."""
    tenant_id = tenant_id or "default"
    if scope == "per-tenant":
        return f"t:{tenant_id}"
    if scope == "per-organization":
        target = org_id or user_id
        return f"t:{tenant_id}:o:{target}" if org_id else f"t:{tenant_id}:u:{user_id}"
    return f"t:{tenant_id}:u:{user_id}"


def default_scope_for(integration_key: str) -> str:
    """Return the default scope mode for an integration."""
    if integration_key.lower() in _SCOPE_PER_ORG:
        return "per-organization"
    return "per-user"
