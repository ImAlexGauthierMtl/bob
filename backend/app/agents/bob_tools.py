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
            "description": "Create a new organization in the CRM. Accepts all organization fields. Automatically checks for duplicates before creating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Organization name",
                    },
                    "website": {
                        "type": "string",
                        "description": "Organization website URL",
                    },
                    "industry": {
                        "type": "string",
                        "description": "Industry sector",
                    },
                    "phone": {
                        "type": "string",
                        "description": "Phone number",
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address",
                    },
                    "address_street": {
                        "type": "string",
                        "description": "Street address",
                    },
                    "address_city": {
                        "type": "string",
                        "description": "City",
                    },
                    "address_state": {
                        "type": "string",
                        "description": "State/Province",
                    },
                    "address_country": {
                        "type": "string",
                        "description": "Country",
                    },
                    "address_postal_code": {
                        "type": "string",
                        "description": "Postal/ZIP code",
                    },
                    "status": {
                        "type": "string",
                        "description": "Organization status",
                        "enum": ["ACTIVE", "INACTIVE", "PROSPECT", "CUSTOMER", "CHURNED"],
                    },
                    "org_type": {
                        "type": "string",
                        "description": "Organization type",
                        "enum": ["CORPORATION", "SMB", "STARTUP", "GOVERNMENT", "NONPROFIT", "OTHER"],
                    },
                    "employee_count": {
                        "type": "integer",
                        "description": "Number of employees",
                    },
                    "annual_revenue": {
                        "type": "number",
                        "description": "Annual revenue in dollars",
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the organization",
                    },
                    "linkedin_url": {
                        "type": "string",
                        "description": "LinkedIn company page URL",
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
            "name": "show_artifact",
            "description": (
                "Display a rich inline artifact in the chat. UI-ONLY — does NOT create/modify data. "
                "Choose the type that BEST matches the data structure:\n"
                "- card types (opportunity/contact/organization): single-record detail → use fields[]\n"
                "- search_results: numbered selection list → use fields[]\n"
                "- data_table: multi-column list (contacts, opps, orders) → use columns[] + rows[][]\n"
                "- kpi_summary: 2-4 numeric metrics side by side → use items[]\n"
                "- progress_card: projection with progress bar → use items[] with percent\n"
                "- checklist: action items with checkboxes → use items[]\n"
                "- action_plan: phased timeline with tasks → use sections[]\n"
                "- info_list: bullet points with icons → use items[] with icon\n"
                "- pipeline: progress bars by stage → use items[] with percent\n"
                "- activity_card: single activity detail (call/email/meeting/task/note) → fields[0]=type, rest=detail fields\n"
                "- entity_timeline: chronological activity list → use items[] with icon+time\n"
                "- comparison_table: 360° entity summary with grouped sections → use sections[]\n"
                "- alert_banner: confirmation/error/warning banner → fields[0]=severity(success/error/warning), fields[1]=description\n"
                "- metric_trend: advisor projection metrics with trends → use items[] with change+percent\n"
                "- enrichment_profile: enrichment results with sectioned data → use sections[]"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": [
                            "opportunity", "contact", "organization", "search_results",
                            "data_table", "kpi_summary", "progress_card", "checklist",
                            "action_plan", "info_list", "pipeline",
                            "activity_card", "entity_timeline", "comparison_table",
                            "alert_banner", "metric_trend", "enrichment_profile",
                        ],
                        "description": "Display type — pick based on data shape.",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title of the artifact card.",
                    },
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string"},
                                "value": {"type": "string"},
                            },
                            "required": ["label", "value"],
                        },
                        "description": "Label/value pairs for card types and search_results.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["building", "complete"],
                        "default": "building",
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Column headers for data_table.",
                    },
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "description": "Row data for data_table. Each row is an array of cell values matching columns.",
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "label": {"type": "string", "description": "Item label/name"},
                                "value": {"type": "string", "description": "Item value"},
                                "change": {"type": "string", "description": "kpi: change indicator e.g. '+18%'"},
                                "icon": {"type": "string", "description": "info_list: FontAwesome icon e.g. 'fa-circle'"},
                                "percent": {"type": "number", "description": "pipeline/progress: percentage 0-100"},
                                "time": {"type": "string", "description": "action_plan: date/time"},
                                "description": {"type": "string", "description": "Extended description"},
                            },
                            "required": ["label", "value"],
                        },
                        "description": "Items for kpi_summary, pipeline, progress_card, checklist, info_list.",
                    },
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "subtitle": {"type": "string"},
                                "badge": {"type": "string", "description": "Optional badge text e.g. 'Priority'"},
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "label": {"type": "string"},
                                            "value": {"type": "string"},
                                            "description": {"type": "string"},
                                            "time": {"type": "string"},
                                        },
                                        "required": ["label"],
                                    },
                                },
                            },
                            "required": ["title", "items"],
                        },
                        "description": "Sections for action_plan (phased timeline).",
                    },
                },
                "required": ["type", "title"],
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
    {
        "type": "function",
        "function": {
            "name": "enrich_account",
            "description": (
                "Launch Bob's Rolodex deep enrichment on an existing account. "
                "Call this when the user agrees to enrich after account creation "
                "(e.g. they say 'yes' to 'Make my magic with my rolodex?'). "
                "Returns enriched company data as an artifact displayed in the chat."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization to enrich",
                    },
                },
                "required": ["organization_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_rolodex",
            "description": (
                "Search Bob's Rolodex (company directory) for organizations matching a name or query. "
                "Returns a numbered list of matching businesses with name, address, phone, website, and industry. "
                "Use this FIRST when the user wants to add/create an account, BEFORE calling open_create_dialog. "
                "Present the results to the user so they can pick one."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Business name or search query",
                    },
                },
                "required": ["query"],
            },
        },
    },
    # ── Organization management tools ─────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_organization",
            "description": "Get full details of an organization by ID. Returns all fields including contacts count, opportunities count, and BCC profile.",
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization",
                    },
                },
                "required": ["organization_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_organization",
            "description": "Update one or more fields of an existing organization. Only provide the fields you want to change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization to update",
                    },
                    "name": {"type": "string", "description": "New organization name"},
                    "website": {"type": "string", "description": "Website URL"},
                    "industry": {"type": "string", "description": "Industry sector"},
                    "phone": {"type": "string", "description": "Phone number"},
                    "email": {"type": "string", "description": "Email address"},
                    "address_street": {"type": "string", "description": "Street address"},
                    "address_city": {"type": "string", "description": "City"},
                    "address_state": {"type": "string", "description": "State/Province"},
                    "address_country": {"type": "string", "description": "Country"},
                    "address_postal_code": {"type": "string", "description": "Postal/ZIP code"},
                    "status": {
                        "type": "string",
                        "description": "Organization status",
                        "enum": ["ACTIVE", "INACTIVE", "PROSPECT", "CUSTOMER", "CHURNED"],
                    },
                    "org_type": {
                        "type": "string",
                        "description": "Organization type",
                        "enum": ["CORPORATION", "SMB", "STARTUP", "GOVERNMENT", "NONPROFIT", "OTHER"],
                    },
                    "employee_count": {"type": "integer", "description": "Number of employees"},
                    "annual_revenue": {"type": "number", "description": "Annual revenue in dollars"},
                    "description": {"type": "string", "description": "Description of the organization"},
                    "linkedin_url": {"type": "string", "description": "LinkedIn company page URL"},
                },
                "required": ["organization_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_organization",
            "description": "Soft-delete an organization. Will fail if there are linked contacts or opportunities — they must be removed first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization to delete",
                    },
                },
                "required": ["organization_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_organization_contacts",
            "description": "List all contacts linked to an organization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max contacts to return (default 20)",
                    },
                },
                "required": ["organization_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_organization_opportunities",
            "description": "List all sales opportunities linked to an organization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max opportunities to return (default 20)",
                    },
                },
                "required": ["organization_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_organization_owner",
            "description": "Assign or change the owner of an organization. The owner is the sales rep responsible for this account.",
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization",
                    },
                    "owner_email": {
                        "type": "string",
                        "description": "Email of the new owner (must be a user in the system)",
                    },
                },
                "required": ["organization_id", "owner_email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_organization_summary",
            "description": (
                "Get a comprehensive summary of the relationship with an organization. "
                "Includes organization details, contacts, open opportunities, recent activities, "
                "and BCC intelligence profile. Use this when the user asks for an overview or summary."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {
                        "type": "string",
                        "description": "UUID of the organization",
                    },
                },
                "required": ["organization_id"],
            },
        },
    },
    # ── Contact management tools ──────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_contact",
            "description": "Get full details of a contact by ID. Returns all fields including linked organization, opportunities count, and activities count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "UUID of the contact",
                    },
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_contact",
            "description": "Update one or more fields of an existing contact. Only provide the fields you want to change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "UUID of the contact to update",
                    },
                    "first_name": {"type": "string", "description": "First name"},
                    "last_name": {"type": "string", "description": "Last name"},
                    "email": {"type": "string", "description": "Email address"},
                    "phone": {"type": "string", "description": "Phone number"},
                    "mobile": {"type": "string", "description": "Mobile number"},
                    "job_title": {"type": "string", "description": "Job title"},
                    "department": {"type": "string", "description": "Department"},
                    "seniority": {"type": "string", "description": "Seniority level"},
                    "linkedin_url": {"type": "string", "description": "LinkedIn profile URL"},
                    "notes": {"type": "string", "description": "Notes about the contact"},
                    "status": {
                        "type": "string",
                        "description": "Contact status",
                        "enum": ["ACTIVE", "INACTIVE", "LEAD"],
                    },
                    "organization_id": {"type": "string", "description": "UUID of the organization to link"},
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_contact",
            "description": "Soft-delete a contact. Will fail if there are linked opportunities — they must be reassigned first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "UUID of the contact to delete",
                    },
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_contact_activities",
            "description": "List all activities linked to a contact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "UUID of the contact",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max activities to return (default 20)",
                    },
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_contact_opportunities",
            "description": "List all sales opportunities linked to a contact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "UUID of the contact",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max opportunities to return (default 20)",
                    },
                },
                "required": ["contact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contact_summary",
            "description": (
                "Get a comprehensive 360° view of a contact. "
                "Includes contact details, linked organization, opportunities, "
                "recent activities, and engagement score."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "string",
                        "description": "UUID of the contact",
                    },
                },
                "required": ["contact_id"],
            },
        },
    },
    # ── Opportunity management tools ──────────────────────────
    {
        "type": "function",
        "function": {
            "name": "get_opportunity",
            "description": "Get full details of an opportunity by ID. Returns all fields including linked organization, contact, products, and activities count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                        "description": "UUID of the opportunity",
                    },
                },
                "required": ["opportunity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_opportunity",
            "description": "Update one or more fields of an existing opportunity. Only provide the fields you want to change. Use this to advance stages, update amounts, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                        "description": "UUID of the opportunity to update",
                    },
                    "name": {"type": "string", "description": "Opportunity name"},
                    "description": {"type": "string", "description": "Description"},
                    "stage": {
                        "type": "string",
                        "description": "Pipeline stage",
                        "enum": ["PROSPECTING", "QUALIFICATION", "PROPOSAL", "NEGOTIATION", "CLOSED_WON", "CLOSED_LOST"],
                    },
                    "priority": {
                        "type": "string",
                        "description": "Priority level",
                        "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                    },
                    "amount": {"type": "number", "description": "Deal value"},
                    "probability": {"type": "number", "description": "Win probability 0-100"},
                    "close_date": {"type": "string", "description": "Expected close date (YYYY-MM-DD)"},
                    "source": {"type": "string", "description": "Lead source"},
                    "organization_id": {"type": "string", "description": "UUID of the organization"},
                    "contact_id": {"type": "string", "description": "UUID of the primary contact"},
                },
                "required": ["opportunity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_opportunity",
            "description": "Soft-delete an opportunity. Will fail if there are linked quotes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                        "description": "UUID of the opportunity to delete",
                    },
                },
                "required": ["opportunity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_opportunity_activities",
            "description": "List all activities linked to an opportunity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                        "description": "UUID of the opportunity",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max activities to return (default 20)",
                    },
                },
                "required": ["opportunity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_opportunity_summary",
            "description": (
                "Get a comprehensive view of an opportunity. "
                "Includes deal details, organization, contact, products, "
                "recent activities, and pipeline position."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "opportunity_id": {
                        "type": "string",
                        "description": "UUID of the opportunity",
                    },
                },
                "required": ["opportunity_id"],
            },
        },
    },
    # ── Activity management tools ─────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "create_activity",
            "description": "Create a new activity (call, email, meeting, task, or note) in the CRM. Can be linked to organizations, contacts, and opportunities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Activity subject/title",
                    },
                    "activity_type": {
                        "type": "string",
                        "description": "Type of activity",
                        "enum": ["CALL", "EMAIL", "MEETING", "TASK", "NOTE"],
                    },
                    "description": {"type": "string", "description": "Activity description/notes"},
                    "priority": {
                        "type": "string",
                        "description": "Priority level",
                        "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                        "default": "MEDIUM",
                    },
                    "due_date": {"type": "string", "description": "Due date (ISO format YYYY-MM-DDTHH:MM:SS)"},
                    "assigned_to": {"type": "string", "description": "Email of the person assigned"},
                    "organization_id": {"type": "string", "description": "UUID of linked organization"},
                    "contact_id": {"type": "string", "description": "UUID of linked contact"},
                    "opportunity_id": {"type": "string", "description": "UUID of linked opportunity"},
                },
                "required": ["subject", "activity_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_activity",
            "description": "Get full details of an activity by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "UUID of the activity",
                    },
                },
                "required": ["activity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_activity",
            "description": "Update one or more fields of an existing activity. Only provide the fields you want to change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "UUID of the activity to update",
                    },
                    "subject": {"type": "string", "description": "Subject/title"},
                    "description": {"type": "string", "description": "Description/notes"},
                    "activity_type": {
                        "type": "string",
                        "enum": ["CALL", "EMAIL", "MEETING", "TASK", "NOTE"],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                    },
                    "status": {
                        "type": "string",
                        "enum": ["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"],
                    },
                    "due_date": {"type": "string", "description": "Due date (ISO format)"},
                    "assigned_to": {"type": "string", "description": "Assigned to (email)"},
                },
                "required": ["activity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_activity",
            "description": "Soft-delete an activity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "UUID of the activity to delete",
                    },
                },
                "required": ["activity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_activity",
            "description": "Mark an activity as completed. Shortcut for update_activity with status=COMPLETED.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_id": {
                        "type": "string",
                        "description": "UUID of the activity to complete",
                    },
                },
                "required": ["activity_id"],
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



# ── IMPORTANT ──────────────────────────────────────────────────
# Tool EXECUTION has been consolidated into tool_executor.py.
# This file only provides tool DEFINITIONS (BOB_TOOLS) and
# dynamic tool loading (load_tools_from_bcc).
# Do NOT add execution logic here.
# ──────────────────────────────────────────────────────────────

