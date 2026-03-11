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
            "name": "navigate_to",
            "description": "Navigate the user to a page in the CRM application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "enum": [
                            "dashboard", "organizations", "contacts",
                            "opportunities", "quotes", "activities",
                            "settings", "settings/team", "knowledge-base",
                            "template/crm-mastery",
                        ],
                        "description": "The page to navigate to.",
                    },
                },
                "required": ["page"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_create_dialog",
            "description": "CRITICAL: Navigate to an entity list page and open the create/add new item dialog. ALWAYS use this if the user says 'Add', 'Create', 'New', 'Ajouter', 'Créer' (e.g., 'Add TELUS mobility to my CRM'). If the user mentions a name, pass it so the search can be pre-filled.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "enum": [
                            "organization", "contact", "opportunity",
                            "quote", "activity",
                        ],
                        "description": "The entity type to create.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional name/company name mentioned by the user to pre-fill the search field.",
                    },
                },
                "required": ["entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ui_update_input",
            "description": "CRITICAL: Update the text in an open search or creation dialog. Use this to correct spelling mistakes or initiate a search/parsing. Set submit=true if the user is finished dictating and wants to run the search or parsing process.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to input into the field.",
                    },
                    "submit": {
                        "type": "boolean",
                        "description": "Whether to auto-submit/search after changing the text.",
                    },
                },
                "required": ["text", "submit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ui_select_result",
            "description": "CRITICAL: Select a specific numbered result from a list in the UI. For example, if the user says 'choose number 2', you would pass 2.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "The 1-based index of the item to select (e.g. 1 for the first item).",
                    },
                },
                "required": ["index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ui_switch_tab",
            "description": "CRITICAL: Switch or open a specific tab inside the current view (or within an entity's profile). Usually used when a user asks to see 'Profile', 'Contacts', 'Activities', 'Account & Security', 'Notifications', 'Automation', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tab_name": {
                        "type": "string",
                        "description": "The exact name or identifier of the tab to switch to (e.g., 'profile', 'contacts', 'overview', 'security', 'automation'). Should be lowercase.",
                    },
                },
                "required": ["tab_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_crm_training",
            "description": "CRITICAL: Start the CRM Mastery training session. Navigate the user to the training page immediately. Call this whenever the user asks for training, says 'I want to do my training', 'start the CRM training', 'je veux faire ma formation', or complains that the presentation/training is not on screen (e.g. 'ne montre pas la présentation', 'you should bring it'). Do NOT answer verbally, JUST call this tool.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_open_entity",
            "description": "CRITICAL: Used ONLY when the user asks to OPEN or ACCESS an existing entity (like 'open Bell', 'go to John Doe'). It searches for it, and if found, directly navigates the UI to its detailed page. Do NOT use this tool if the user says 'Add', 'Create', 'New'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "enum": ["organization", "contact", "opportunity"],
                        "description": "The type of entity to find and open.",
                    },
                    "query": {
                        "type": "string",
                        "description": "The name or email of the entity to search for.",
                    },
                },
                "required": ["entity", "query"],
            },
        },
    },
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
            "description": "PREFERRED: Create a new contact DIRECTLY in the CRM when the user provides name and/or email. Use this instead of open_create_dialog when you have the contact info. If a company name is provided, it will be linked to the matching organization.",
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
                "required": ["first_name"],
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
            "name": "create_opportunity",
            "description": "Create a new sales opportunity in the CRM. Link it to an organization and/or contact. Defaults to PROSPECTING stage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Opportunity name (e.g. 'PSU - Service Integration')",
                    },
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization to link (optional)",
                    },
                    "contact_id": {
                        "type": "string",
                        "description": "UUID of the primary contact (optional)",
                    },
                    "stage": {
                        "type": "string",
                        "description": "Pipeline stage (default: PROSPECTING)",
                        "enum": ["PROSPECTING", "QUALIFICATION", "PROPOSAL", "NEGOTIATION", "CLOSED_WON", "CLOSED_LOST"],
                        "default": "PROSPECTING",
                    },
                    "source": {
                        "type": "string",
                        "description": "Lead source (e.g. 'Hunter', 'Inbound', 'Referral')",
                    },
                    "amount": {
                        "type": "number",
                        "description": "Estimated deal value (optional)",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "link_product_to_opportunity",
            "description": "Attach a product from the catalog to an existing opportunity. Snapshots the current product price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                        "description": "UUID of the opportunity",
                    },
                    "product_id": {
                        "type": "string",
                        "description": "UUID of the product to link",
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity (default: 1)",
                        "default": 1,
                    },
                },
                "required": ["opportunity_id", "product_id"],
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
    # ── Training tools ───────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "save_training_note",
            "description": (
                "Save a note during training when the user asks to take a note, "
                "write something down, or remember something. Capture the key insight."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Training session UUID",
                    },
                    "slide_id": {
                        "type": "integer",
                        "description": "Current slide number (0-indexed)",
                    },
                    "content": {
                        "type": "string",
                        "description": "The note content to save",
                    },
                    "note_type": {
                        "type": "string",
                        "description": "Type of note",
                        "enum": ["insight", "action", "important"],
                        "default": "insight",
                    },
                },
                "required": ["session_id", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_missing_element",
            "description": (
                "Log a missing feature, integration, or process that the user identifies "
                "during training. For example: 'we need Zoho integration', "
                "'there should be an auto-follow-up feature', etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Training session UUID",
                    },
                    "label": {
                        "type": "string",
                        "description": "Short label for the missing element (e.g. 'Zoho CRM Integration')",
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the missing element",
                        "enum": ["integration", "feature", "process"],
                        "default": "integration",
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed description of what's missing and why",
                    },
                },
                "required": ["session_id", "label"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "change_training_slide",
            "description": (
                "Navigate training slides when the user says 'next slide', "
                "'previous slide', 'go to slide 5', etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "description": "Navigation direction",
                        "enum": ["next", "previous", "goto"],
                    },
                    "slide_number": {
                        "type": "integer",
                        "description": "Target slide number (1-indexed, only for 'goto' direction)",
                    },
                },
                "required": ["direction"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_deep_agent",
            "description": (
                "Invoke the Deep Agent to build or enrich the BCC cognitive structure. "
                "Use when the user asks to set up domains, intents, or tasks in bulk, "
                "or to configure Bob's capabilities. Examples: 'Configure Bob', "
                "'Set up the BCC', 'Build the cognitive structure', 'Make this happen to the BCC'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "What to build or enrich in the BCC — the user's instruction.",
                    },
                },
                "required": ["instruction"],
            },
        },
    },
]


def load_tools_from_bcc(db, tenant_id: str) -> list[dict]:
    """Load tool schemas from BCC TaskTemplate context, falling back to hardcoded."""
    try:
        from app.domain.entities.bcc_entities import BccTaskTemplate

        templates = db.query(BccTaskTemplate).filter_by(tenant_id=tenant_id).all()
        bcc_schemas = []
        for t in templates:
            if t.context and t.context.get("tool_schemas"):
                bcc_schemas.extend(t.context["tool_schemas"])
        if bcc_schemas:
            logger.info("tools_loaded_from_bcc", count=len(bcc_schemas))
            return bcc_schemas
    except Exception as e:
        logger.warning("bcc_tool_load_failed", error=str(e))
    return BOB_TOOLS


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
        elif tool_name == "save_training_note":
            return await _save_training_note(db_session, user_id=user_id, **arguments)
        elif tool_name == "save_missing_element":
            return await _save_missing_element(db_session, user_id=user_id, **arguments)
        elif tool_name == "change_training_slide":
            return await _change_training_slide(**arguments)
        elif tool_name == "invoke_deep_agent":
            return await _invoke_deep_agent(db_session, user_id=user_id, **arguments)
        else:
            dynamic_result = await _execute_dynamic_tool(db_session, user_id, tool_name, arguments)
            if dynamic_result is not None:
                return dynamic_result
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
    email: str = "",
    last_name: str = "",
    phone: str = "",
    company: str = "",
) -> str:
    """Create a new contact, optionally linked to an organization."""
    from app.domain.entities.contact import Contact
    from app.domain.entities.organization import Organization

    # Find organization by name if company is provided
    org_id = None
    org_name = ""
    if company:
        org = db_session.query(Organization).filter(
            Organization.name.ilike(f"%{company}%")
        ).first()
        if org:
            org_id = org.id
            org_name = org.name

    contact = Contact(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        organization_id=org_id,
    )
    db_session.add(contact)
    db_session.commit()

    logger.info(
        "tool_contact_created",
        contact_id=str(contact.id),
        email=email,
        organization=org_name or None,
        user_id=user_id,
    )

    result = f"Contact created: {first_name} {last_name}"
    if email:
        result += f" ({email})"
    if org_name:
        result += f" — linked to organization '{org_name}'"
    elif company:
        result += f" — organization '{company}' not found, contact created without org link"
    return result


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

    # Get user name + tenant_id for contributor display
    from app.domain.entities.user import User
    user = db_session.query(User).filter(User.id == user_id).first()
    contributor_name = "Bob" if not user else f"{user.first_name} {user.last_name} (via Bob)"
    tenant_id = user.tenant_id if user else "default"

    # Find latest version for this entity+section+perspective
    latest = (
        db_session.query(BccProfileEntry)
        .filter(
            and_(
                BccProfileEntry.tenant_id == tenant_id,
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
        tenant_id=tenant_id,
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

    # Index in RAG for semantic retrieval
    if content:
        try:
            from app.rag.indexer import index_bcc_profile_entry as _rag_index
            _rag_index(
                db=db_session,
                entity_type=entity_type,
                entity_id=entity_id,
                section=section,
                content=content,
                tenant_id=entry.tenant_id,
            )
        except Exception as rag_err:
            logger.warning("rag_index_profile_failed", error=str(rag_err))

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


# ── Training tool implementations ────────────────────────────

async def _save_training_note(
    db_session,
    user_id: str,
    session_id: str,
    content: str,
    slide_id: int = 0,
    note_type: str = "insight",
) -> str:
    """Save a training note to the database."""
    import uuid
    from app.domain.entities.training_models import TrainingNote

    note = TrainingNote(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=user_id,
        slide_id=slide_id,
        content=content,
        note_type=note_type,
    )
    db_session.add(note)
    db_session.commit()

    logger.info(
        "training_note_saved",
        note_id=note.id,
        session_id=session_id,
        note_type=note_type,
    )

    return f"Note saved: '{content[:60]}...' (type: {note_type})"


async def _save_missing_element(
    db_session,
    user_id: str,
    session_id: str,
    label: str,
    category: str = "integration",
    description: str = "",
) -> str:
    """Save a missing element to the database."""
    import uuid
    from app.domain.entities.training_models import TrainingMissingElement

    item = TrainingMissingElement(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=user_id,
        label=label,
        category=category,
        description=description,
    )
    db_session.add(item)
    db_session.commit()

    logger.info(
        "training_missing_saved",
        item_id=item.id,
        session_id=session_id,
        label=label,
        category=category,
    )

    return f"Missing element logged: '{label}' (category: {category})"


async def _change_training_slide(
    direction: str,
    slide_number: int = 0,
) -> str:
    """Return a slide navigation action for the frontend.

    The actual navigation happens on the frontend — this just returns
    a JSON-serializable result that the chat agent sends as an action.
    """
    import json

    result = {"action": "change_slide", "direction": direction}
    if direction == "goto" and slide_number:
        result["slide_number"] = slide_number

    return json.dumps(result)


async def _invoke_deep_agent(
    db_session,
    user_id: str,
    instruction: str,
) -> str:
    """Invoke the Deep Agent to build/enrich BCC structure.

    This is the tool-call path (legacy flow fallback).
    The primary path is via the workflow engine (build_bcc intent).
    """
    from app.agents.deep_agent_graph import run_deep_agent
    from app.domain.entities.user import User

    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        return "Error: user not found."

    try:
        result = await run_deep_agent(
            instruction=instruction,
            tenant_id=user.tenant_id,
            user_id=user_id,
            user_email=user.email or "unknown",
        )
    except Exception as e:
        logger.error("invoke_deep_agent_failed", error=str(e))
        return f"Deep Agent failed: {str(e)}"

    if result.get("error"):
        return f"Deep Agent error: {result['error']}"

    return (
        f"Deep Agent completed: {result.get('domains_created', 0)} domains, "
        f"{result.get('intents_created', 0)} intents, "
        f"{result.get('tasks_created', 0)} tasks created. "
        f"Review: {result.get('review', {}).get('summary', 'N/A')}"
    )


TABLE_MODEL_MAP = {
    "organizations": "app.domain.entities.organization.Organization",
    "contacts": "app.domain.entities.contact.Contact",
    "opportunities": "app.domain.entities.opportunity.Opportunity",
    "activities": "app.domain.entities.activity.Activity",
    "products": "app.domain.entities.product.Product",
}


async def _execute_dynamic_tool(
    db_session,
    user_id: str,
    tool_name: str,
    arguments: dict,
) -> Optional[str]:
    """Execute a BCC-defined dynamic tool via generic ORM query.

    Looks up the tool in BccTaskTemplate.context["tool_schemas"],
    then uses db_table/db_operation from context to run a safe SELECT query.
    Returns None if the tool is not found in BCC (caller falls back to "Unknown tool").
    """
    from app.domain.entities.bcc_entities import BccTaskTemplate
    from app.domain.entities.user import User
    import importlib

    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    tenant_id = user.tenant_id

    templates = db_session.query(BccTaskTemplate).filter(
        BccTaskTemplate.tenant_id == tenant_id,
    ).all()

    target_tpl = None
    for tpl in templates:
        ctx = tpl.context or {}
        tool_prio = ctx.get("tool_priority", [])
        if isinstance(tool_prio, list) and tool_name in tool_prio:
            target_tpl = tpl
            break
        schemas = ctx.get("tool_schemas", [])
        for s in schemas:
            if s.get("function", {}).get("name") == tool_name:
                target_tpl = tpl
                break
        if target_tpl:
            break

    if not target_tpl:
        return None

    ctx = target_tpl.context or {}
    db_table = ctx.get("db_table")
    db_operation = (ctx.get("db_operation") or "SELECT").upper()

    if not db_table or "SELECT" not in db_operation:
        return f"Dynamic tool {tool_name}: read-only operations only."

    table_key = db_table.lower().strip()
    model_path = TABLE_MODEL_MAP.get(table_key)
    if not model_path:
        return f"Dynamic tool {tool_name}: unknown table '{db_table}'."

    module_path, class_name = model_path.rsplit(".", 1)
    mod = importlib.import_module(module_path)
    Model = getattr(mod, class_name)

    try:
        query = db_session.query(Model).filter(Model.tenant_id == tenant_id)

        search_query = arguments.get("query") or arguments.get("search") or arguments.get("name")
        if search_query and hasattr(Model, "name"):
            query = query.filter(Model.name.ilike(f"%{search_query}%"))

        limit = int(arguments.get("limit", 10))
        limit = min(limit, 50)

        if hasattr(Model, "created_at"):
            query = query.order_by(Model.created_at.desc())

        results = query.limit(limit).all()

        if not results:
            return f"No results found for {tool_name}."

        lines = [f"Found {len(results)} result(s):"]
        for i, row in enumerate(results, 1):
            name = getattr(row, "name", None) or getattr(row, "subject", None) or str(row.id)[:8]
            detail_parts = []
            for attr in ("industry", "stage", "email", "category", "status", "amount"):
                val = getattr(row, attr, None)
                if val:
                    detail_parts.append(f"{attr}={val}")
            detail = f" ({', '.join(detail_parts)})" if detail_parts else ""
            lines.append(f"  {i}. {name}{detail}")

        logger.info("dynamic_tool_executed", tool=tool_name, table=db_table, results=len(results))
        return "\n".join(lines)

    except Exception as e:
        logger.error("dynamic_tool_error", tool=tool_name, error=str(e))
        return f"Dynamic tool {tool_name} error: {str(e)}"

