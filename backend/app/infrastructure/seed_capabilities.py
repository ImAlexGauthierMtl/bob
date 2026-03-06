"""Capability seed data — initial capability catalog.

Seeds the CapabilityDefinition table with the full catalog of
capabilities across all scopes: common, module, integration, automation, agent.
"""

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.capability import CapabilityDefinition

logger = structlog.get_logger(__name__)

CAPABILITY_CATALOG = [
    # ── Common (all modules) ──────────────────────────────
    {"code": "common.view_dashboard", "name": "View Dashboard", "scope": "common", "default_enabled": True, "risk_level": "low"},
    {"code": "common.edit_own_profile", "name": "Edit Own Profile", "scope": "common", "default_enabled": True, "risk_level": "low"},
    {"code": "common.view_analytics", "name": "View Analytics", "scope": "common", "default_enabled": True, "risk_level": "low"},
    {"code": "common.export_data", "name": "Export Data", "scope": "common", "default_enabled": False, "risk_level": "medium"},
    {"code": "common.manage_users", "name": "Manage Users", "scope": "common", "default_enabled": False, "risk_level": "high"},
    {"code": "common.manage_departments", "name": "Manage Departments", "scope": "common", "default_enabled": False, "risk_level": "high"},
    {"code": "common.manage_settings", "name": "Manage Settings", "scope": "common", "default_enabled": False, "risk_level": "high"},

    # ── Module: Contacts ──────────────────────────────────
    {"code": "contacts.view", "name": "View Contacts", "scope": "module", "module": "contacts", "default_enabled": True, "risk_level": "low"},
    {"code": "contacts.create", "name": "Create Contacts", "scope": "module", "module": "contacts", "default_enabled": True, "risk_level": "low"},
    {"code": "contacts.edit", "name": "Edit Contacts", "scope": "module", "module": "contacts", "default_enabled": True, "risk_level": "low"},
    {"code": "contacts.delete", "name": "Delete Contacts", "scope": "module", "module": "contacts", "default_enabled": False, "risk_level": "high"},

    # ── Module: Organizations ─────────────────────────────
    {"code": "organizations.view", "name": "View Organizations", "scope": "module", "module": "organizations", "default_enabled": True, "risk_level": "low"},
    {"code": "organizations.create", "name": "Create Organizations", "scope": "module", "module": "organizations", "default_enabled": True, "risk_level": "low"},
    {"code": "organizations.edit", "name": "Edit Organizations", "scope": "module", "module": "organizations", "default_enabled": True, "risk_level": "low"},
    {"code": "organizations.delete", "name": "Delete Organizations", "scope": "module", "module": "organizations", "default_enabled": False, "risk_level": "high"},
    {"code": "organizations.enrich", "name": "Trigger AI Enrichment", "scope": "module", "module": "organizations", "default_enabled": True, "risk_level": "medium"},

    # ── Module: Opportunities ─────────────────────────────
    {"code": "opportunities.view", "name": "View Opportunities", "scope": "module", "module": "opportunities", "default_enabled": True, "risk_level": "low"},
    {"code": "opportunities.create", "name": "Create Opportunities", "scope": "module", "module": "opportunities", "default_enabled": True, "risk_level": "low"},
    {"code": "opportunities.edit", "name": "Edit Opportunities", "scope": "module", "module": "opportunities", "default_enabled": True, "risk_level": "low"},
    {"code": "opportunities.delete", "name": "Delete Opportunities", "scope": "module", "module": "opportunities", "default_enabled": False, "risk_level": "high"},

    # ── Module: Quotes ────────────────────────────────────
    {"code": "quotes.view", "name": "View Quotes", "scope": "module", "module": "quotes", "default_enabled": True, "risk_level": "low"},
    {"code": "quotes.create", "name": "Create Quotes", "scope": "module", "module": "quotes", "default_enabled": True, "risk_level": "low"},
    {"code": "quotes.edit", "name": "Edit Quotes", "scope": "module", "module": "quotes", "default_enabled": True, "risk_level": "low"},
    {"code": "quotes.delete", "name": "Delete Quotes", "scope": "module", "module": "quotes", "default_enabled": False, "risk_level": "high"},

    # ── Integration ───────────────────────────────────────
    {"code": "integration.groq", "name": "Use Groq LLM", "scope": "integration", "default_enabled": True, "risk_level": "medium"},
    {"code": "integration.google_maps", "name": "Use Google Maps API", "scope": "integration", "default_enabled": True, "risk_level": "low"},
    {"code": "integration.zoho_sync", "name": "Zoho Desk Sync", "scope": "integration", "default_enabled": False, "risk_level": "medium"},

    # ── Automation ────────────────────────────────────────
    {"code": "automation.view", "name": "View Automations", "scope": "automation", "default_enabled": True, "risk_level": "low"},
    {"code": "automation.create_user", "name": "Create User Workflows", "scope": "automation", "default_enabled": True, "risk_level": "low"},
    {"code": "automation.create_dept", "name": "Create Department Workflows", "scope": "automation", "default_enabled": False, "risk_level": "medium"},
    {"code": "automation.create_company", "name": "Create Company Workflows", "scope": "automation", "default_enabled": False, "risk_level": "high"},
    {"code": "automation.override", "name": "Override Workflows", "scope": "automation", "default_enabled": False, "risk_level": "high"},

    # ── Agent (Bob) ───────────────────────────────────────
    {"code": "bob.suggest", "name": "Bob Can Suggest", "scope": "agent", "default_enabled": True, "risk_level": "low"},
    {"code": "bob.auto_execute", "name": "Bob Can Auto-Execute", "scope": "agent", "default_enabled": False, "risk_level": "high"},
    {"code": "bob.bulk_action", "name": "Bob Can Bulk Action", "scope": "agent", "default_enabled": False, "risk_level": "high"},
    {"code": "bob.ai_parse", "name": "Bob Can AI-Parse Text", "scope": "agent", "default_enabled": True, "risk_level": "low"},
]


def seed_capabilities(db: Session) -> None:
    """Seed all capability definitions if not already seeded."""
    existing_count = db.query(CapabilityDefinition).count()
    if existing_count >= len(CAPABILITY_CATALOG):
        logger.info("capabilities_already_seeded", count=existing_count)
        return

    seeded = 0
    for cap_data in CAPABILITY_CATALOG:
        existing = db.query(CapabilityDefinition).filter(
            CapabilityDefinition.code == cap_data["code"]
        ).first()
        if existing:
            continue

        cap = CapabilityDefinition(**cap_data)
        db.add(cap)
        seeded += 1

    db.commit()
    logger.info("capabilities_seeded", count=seeded)
