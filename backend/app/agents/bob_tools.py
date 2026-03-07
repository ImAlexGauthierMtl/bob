"""Bob CRM tools — function calling definitions for Qwen3.

These tools let Bob perform CRM actions during conversation:
- Search contacts/organizations
- Create new records
- Get pipeline stats
- Update BCC knowledge profiles (versioned, multi-perspective)
- Read BCC knowledge profiles

Tools are defined as Pydantic models and converted to OpenAI-compatible
tool definitions for Qwen3's function calling capability.
"""

import structlog
from typing import Optional

logger = structlog.get_logger(__name__)


# ── Tool definitions (OpenAI format for Qwen3) ──────────────

BOB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_contacts",
            "description": "Search CRM contacts by name, email, or company. Returns matching contacts with their details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — name, email, or company name",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_organizations",
            "description": "Search CRM organizations by name or domain. Returns matching organizations with their details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query — organization name or domain",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_stats",
            "description": "Get summary statistics for the sales pipeline — total opportunities, value by stage, win rate.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_contact",
            "description": "Create a new contact in the CRM. Requires at least first name and email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {
                        "type": "string",
                        "description": "Contact's first name",
                    },
                    "last_name": {
                        "type": "string",
                        "description": "Contact's last name",
                    },
                    "email": {
                        "type": "string",
                        "description": "Contact's email address",
                    },
                    "phone": {
                        "type": "string",
                        "description": "Contact's phone number (optional)",
                    },
                    "company": {
                        "type": "string",
                        "description": "Company/organization name (optional)",
                    },
                },
                "required": ["first_name", "email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_organization",
            "description": "Create a new organization in the CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Organization name",
                    },
                    "website": {
                        "type": "string",
                        "description": "Organization website URL (optional)",
                    },
                    "industry": {
                        "type": "string",
                        "description": "Industry sector (optional)",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_activities",
            "description": "Get recent activities (calls, emails, meetings) from the CRM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent activities to return (default 10)",
                        "default": 10,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bcc_update_profile",
            "description": (
                "Add or update a knowledge profile entry for a BCC entity. "
                "This creates a new versioned entry — previous versions are preserved. "
                "Supports multi-perspective knowledge: CEO, CFO, Director, Employee viewpoints. "
                "Use sections like: description, vision, mission, culture, competition, "
                "best_practices, expectations, deliverables, sop, kpis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": (
                            "Type of BCC entity: industry, career, skill_template, "
                            "task_template, organization, department, team, role, regulation"
                        ),
                        "enum": [
                            "industry", "career", "skill_template", "task_template",
                            "organization", "department", "team", "role", "regulation",
                        ],
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "UUID of the entity to update",
                    },
                    "section": {
                        "type": "string",
                        "description": (
                            "Profile section to update (e.g. description, vision, mission, "
                            "culture, competition, best_practices, expectations, sop, kpis)"
                        ),
                    },
                    "content": {
                        "type": "string",
                        "description": "The text content to store for this section",
                    },
                    "perspective": {
                        "type": "string",
                        "description": "Viewpoint perspective (default: general)",
                        "enum": ["general", "ceo", "cfo", "director", "employee"],
                        "default": "general",
                    },
                },
                "required": ["entity_type", "entity_id", "section", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bcc_get_profile",
            "description": (
                "Get the knowledge profile for a BCC entity. Returns all active "
                "profile sections with their content and perspectives."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Type of BCC entity",
                        "enum": [
                            "industry", "career", "skill_template", "task_template",
                            "organization", "department", "team", "role", "regulation",
                        ],
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "UUID of the entity",
                    },
                },
                "required": ["entity_type", "entity_id"],
            },
        },
    },
]


# ── Tool executors ───────────────────────────────────────────

async def execute_tool(
    tool_name: str,
    arguments: dict,
    db_session,
    user_id: str,
) -> str:
    """Execute a tool call and return the result as a string.

    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments from the LLM
        db_session: SQLAlchemy database session
        user_id: Current user's ID

    Returns:
        String result to feed back to the LLM
    """
    logger.info(
        "tool_call",
        tool=tool_name,
        args=arguments,
        user_id=user_id,
    )

    try:
        if tool_name == "search_contacts":
            return await _search_contacts(db_session, **arguments)
        elif tool_name == "search_organizations":
            return await _search_organizations(db_session, **arguments)
        elif tool_name == "get_pipeline_stats":
            return await _get_pipeline_stats(db_session)
        elif tool_name == "create_contact":
            return await _create_contact(db_session, user_id=user_id, **arguments)
        elif tool_name == "create_organization":
            return await _create_organization(db_session, user_id=user_id, **arguments)
        elif tool_name == "get_recent_activities":
            return await _get_recent_activities(db_session, **arguments)
        elif tool_name == "bcc_update_profile":
            return await _bcc_update_profile(db_session, user_id=user_id, **arguments)
        elif tool_name == "bcc_get_profile":
            return await _bcc_get_profile(db_session, **arguments)
        else:
            return f"Unknown tool: {tool_name}"
    except Exception as e:
        logger.error("tool_execution_error", tool=tool_name, error=str(e))
        return f"Error executing {tool_name}: {str(e)}"


# ── Tool implementations ─────────────────────────────────────

async def _search_contacts(db_session, query: str, limit: int = 5) -> str:
    """Search contacts in the database."""
    from app.domain.entities.contact import Contact
    from sqlalchemy import or_

    results = db_session.query(Contact).filter(
        or_(
            Contact.first_name.ilike(f"%{query}%"),
            Contact.last_name.ilike(f"%{query}%"),
            Contact.email.ilike(f"%{query}%"),
        )
    ).limit(limit).all()

    if not results:
        return f"No contacts found matching '{query}'."

    lines = [f"Found {len(results)} contact(s):"]
    for c in results:
        lines.append(f"- {c.first_name} {c.last_name} ({c.email})")
    return "\n".join(lines)


async def _search_organizations(db_session, query: str, limit: int = 5) -> str:
    """Search organizations in the database."""
    from app.domain.entities.organization import Organization

    results = db_session.query(Organization).filter(
        Organization.name.ilike(f"%{query}%")
    ).limit(limit).all()

    if not results:
        return f"No organizations found matching '{query}'."

    lines = [f"Found {len(results)} organization(s):"]
    for o in results:
        website = getattr(o, "website", "") or ""
        lines.append(f"- {o.name} ({website})")
    return "\n".join(lines)


async def _get_pipeline_stats(db_session) -> str:
    """Get pipeline statistics."""
    from app.domain.entities.opportunity import Opportunity
    from sqlalchemy import func

    total = db_session.query(func.count(Opportunity.id)).scalar() or 0
    total_value = db_session.query(func.sum(Opportunity.value)).scalar() or 0

    return (
        f"Pipeline stats:\n"
        f"- Total opportunities: {total}\n"
        f"- Total pipeline value: ${total_value:,.0f}"
    )


async def _create_contact(
    db_session,
    user_id: str,
    first_name: str,
    email: str,
    last_name: str = "",
    phone: str = "",
    company: str = "",
) -> str:
    """Create a new contact."""
    from app.domain.entities.contact import Contact

    contact = Contact(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
    )
    db_session.add(contact)
    db_session.commit()

    logger.info(
        "tool_contact_created",
        contact_id=str(contact.id),
        email=email,
        user_id=user_id,
    )

    return f"Contact created: {first_name} {last_name} ({email})"


async def _create_organization(
    db_session,
    user_id: str,
    name: str,
    website: str = "",
    industry: str = "",
) -> str:
    """Create a new organization."""
    from app.domain.entities.organization import Organization

    org = Organization(name=name)
    if website:
        org.website = website
    db_session.add(org)
    db_session.commit()

    logger.info(
        "tool_organization_created",
        org_id=str(org.id),
        name=name,
        user_id=user_id,
    )

    return f"Organization created: {name}"


async def _get_recent_activities(db_session, limit: int = 10) -> str:
    """Get recent activities."""
    from app.domain.entities.activity import Activity

    results = db_session.query(Activity).order_by(
        Activity.created_at.desc()
    ).limit(limit).all()

    if not results:
        return "No recent activities found."

    lines = [f"Last {len(results)} activities:"]
    for a in results:
        lines.append(f"- [{a.activity_type}] {a.subject}")
    return "\n".join(lines)


async def _bcc_update_profile(
    db_session,
    user_id: str,
    entity_type: str,
    entity_id: str,
    section: str,
    content: str,
    perspective: str = "general",
    conversation_id: Optional[str] = None,
) -> str:
    """Add a versioned profile entry to a BCC entity."""
    from app.domain.entities.bcc_entities import BccProfileEntry
    from app.domain.entities.base import generate_uuid
    from sqlalchemy import and_

    # Get user name for contributor display
    from app.domain.entities.user import User
    user = db_session.query(User).filter(User.id == user_id).first()
    contributor_name = "Bob" if not user else f"{user.first_name} {user.last_name} (via Bob)"

    # Find latest version for this entity+section+perspective
    latest = (
        db_session.query(BccProfileEntry)
        .filter(
            and_(
                BccProfileEntry.entity_type == entity_type,
                BccProfileEntry.entity_id == entity_id,
                BccProfileEntry.section == section,
                BccProfileEntry.perspective == perspective,
            )
        )
        .order_by(BccProfileEntry.version.desc())
        .first()
    )

    new_version = (latest.version + 1) if latest else 1

    # Deactivate previous active version
    if latest and latest.is_active:
        latest.is_active = False

    # Create new entry
    entry = BccProfileEntry(
        id=generate_uuid(),
        entity_type=entity_type,
        entity_id=entity_id,
        section=section,
        content=content,
        perspective=perspective,
        version=new_version,
        is_active=True,
        contributed_by=user_id,
        contributor_name=contributor_name,
        contribution_method="conversation",
        conversation_id=conversation_id,
    )
    db_session.add(entry)
    db_session.commit()

    logger.info(
        "bcc_profile_updated",
        entity_type=entity_type,
        entity_id=entity_id,
        section=section,
        perspective=perspective,
        version=new_version,
        user_id=user_id,
    )

    return (
        f"Profile updated: {entity_type}/{entity_id} → "
        f"section='{section}', perspective='{perspective}', "
        f"version={new_version}. The knowledge base has been enriched."
    )


async def _bcc_get_profile(
    db_session,
    entity_type: str,
    entity_id: str,
) -> str:
    """Get all active profile entries for a BCC entity."""
    from app.domain.entities.bcc_entities import BccProfileEntry
    from sqlalchemy import and_

    entries = (
        db_session.query(BccProfileEntry)
        .filter(
            and_(
                BccProfileEntry.entity_type == entity_type,
                BccProfileEntry.entity_id == entity_id,
                BccProfileEntry.is_active == True,
            )
        )
        .order_by(BccProfileEntry.section)
        .all()
    )

    if not entries:
        return f"No profile data found for {entity_type}/{entity_id}. The profile is empty."

    lines = [f"Profile for {entity_type}/{entity_id} ({len(entries)} entries):"]
    current_section = None
    for e in entries:
        if e.section != current_section:
            current_section = e.section
            lines.append(f"\n## {current_section.replace('_', ' ').title()}")
        perspective_label = f"[{e.perspective.upper()}]" if e.perspective != "general" else ""
        content_preview = (e.content[:200] + "...") if e.content and len(e.content) > 200 else (e.content or "(structured data)")
        lines.append(f"  {perspective_label} v{e.version}: {content_preview}")

    return "\n".join(lines)
