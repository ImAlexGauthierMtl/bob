"""Seed BCC cognitive structure — Domains, Intents, Tasks aligned to Bob's runtime.

Creates the full Domain -> Intent -> TaskTemplate -> BccIntentTask chain
that mirrors the hardcoded SUPPORTED_INTENTS and @workflow() decorators.

Every task context is deeply enriched so a weak LLM can follow the procedure
like a recipe — no guessing, explicit inputs/outputs/response format.
"""

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.base import generate_uuid
from app.domain.entities.bcc_entities import (
    BccDomain, BccIntent, BccIntentTask, BccTaskTemplate,
)

logger = structlog.get_logger(__name__)


# ═══════════════════════════════════════════════════════════════
#  DOMAIN 1: CRM SALES
# ═══════════════════════════════════════════════════════════════

CRM_SALES = {
    "name": "CRM Sales",
    "description": "Workflows for creating prospects, contacts, searching entities, and navigating the CRM. These are the core sales actions that move deals forward.",
    "icon": "fa-solid fa-handshake",
    "intents": [
        {
            "name": "create_prospect",
            "workflow_key": "create_prospect",
            "description": "Full prospect creation pipeline: search for existing org → create org if new → create contact → create opportunity. This is a multi-step workflow that pauses to let the user choose an existing org or create a new one.",
            "category": "sales",
            "trigger_phrases": [
                "nouveau prospect", "new prospect", "ajoute une opportunité",
                "crée un prospect", "add opportunity", "nouvelle opp",
                "nouveau client", "new deal", "ajouter un deal",
            ],
            "tasks": [
                {
                    "name": "Search for existing organization",
                    "tool_name": "search_organizations",
                    "description": "Search the Organization table by name (ilike) to avoid duplicates. Show up to 5 results. If matches found, pause and let user pick or create new.",
                    "context": {
                        "procedure": [
                            "1. Extract org_name from user entities",
                            "2. Query Organization WHERE tenant_id=current AND name ILIKE '%{org_name}%' LIMIT 5",
                            "3. IF results found: emit action search_entity(entity='organization', page='organizations', name=org_name)",
                            "4. Also emit ui_update_input(text=org_name, submit=True) to trigger the UI search",
                            "5. Pause workflow with numbered list: '1. OrgName — industry' for each result",
                            "6. Add instruction: 'Ou tapez « nouveau » pour créer une nouvelle organisation.'",
                            "7. IF no results: skip straight to Create Organization step",
                        ],
                        "tool_priority": ["search_organizations"],
                        "required_info": ["org_name"],
                        "db_table": "organizations",
                        "db_filter": "name ILIKE '%{org_name}%'",
                        "db_limit": 5,
                        "pause_resume_key": "prospect_org_selected",
                        "expected_output": "List of matching orgs or empty → proceed to creation",
                        "response_format": "Numbered list with org name + industry, or direct creation flow",
                        "model_hint": "fast",
                    },
                },
                {
                    "name": "Create organization record",
                    "tool_name": "create_organization",
                    "description": "Insert a new Organization record with the name from user input. Store the org_id in workflow state for linking contact and opportunity.",
                    "context": {
                        "procedure": [
                            "1. Create Organization(tenant_id=current, name=org_name, created_by=user_email)",
                            "2. db.add() + db.flush() to get the ID",
                            "3. Store org.id in workflow state for next steps",
                            "4. add_tool_step('create organization')",
                        ],
                        "tool_priority": ["create_organization"],
                        "required_info": ["org_name"],
                        "db_table": "organizations",
                        "db_operation": "INSERT",
                        "expected_output": "org_id (UUID) stored in state",
                        "model_hint": "fast",
                    },
                },
                {
                    "name": "Create contact linked to organization",
                    "tool_name": "create_contact",
                    "description": "Insert a Contact record linked to the organization. Use first_name, last_name, email, phone from user entities.",
                    "context": {
                        "procedure": [
                            "1. Create Contact(tenant_id, organization_id=org.id, first_name, last_name, email, phone, created_by)",
                            "2. db.add() + db.flush()",
                            "3. add_tool_step('create contact')",
                        ],
                        "tool_priority": ["create_contact"],
                        "required_info": ["contact_first", "contact_last"],
                        "optional_info": ["email", "phone"],
                        "db_table": "contacts",
                        "db_operation": "INSERT",
                        "expected_output": "contact_id linked to org_id",
                        "model_hint": "fast",
                    },
                },
                {
                    "name": "Create opportunity linked to org and contact",
                    "tool_name": "create_opportunity",
                    "description": "Insert an Opportunity record with name='{product} — {org}', amount from entities, stage=QUALIFICATION. Links to org and contact.",
                    "context": {
                        "procedure": [
                            "1. Build opp_name = '{product_name} — {org_name}' or '{org_name} — Nouvelle opportunité'",
                            "2. Create Opportunity(tenant_id, name=opp_name, organization_id, contact_id, amount, stage='QUALIFICATION', created_by)",
                            "3. db.add() + db.commit()",
                            "4. add_tool_step('create opportunity')",
                            "5. Return success: '✅ Opportunité créée : **{opp_name}**\\nOrganisation : **{org}**\\nContact : **{name}** ({email})\\nValeur : **{amount}$**'",
                        ],
                        "tool_priority": ["create_opportunity"],
                        "required_info": ["org_id", "contact_id"],
                        "optional_info": ["product_name", "amount", "quantity"],
                        "db_table": "opportunities",
                        "db_operation": "INSERT",
                        "expected_output": "✅ confirmation message with org/contact/opp details",
                        "response_format": "✅ Opportunité créée : **{name}**\nOrganisation : **{org}**\nContact : **{contact}** ({email})\nValeur : **{amount}$**",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "create_contact",
            "workflow_key": "create_contact",
            "description": "Create a standalone contact, optionally linked to an existing organization. Searches org by name if provided, then inserts the contact record.",
            "category": "sales",
            "trigger_phrases": [
                "ajoute un contact", "nouveau contact", "add contact",
                "create contact", "nouveau représentant", "new rep",
            ],
            "tasks": [
                {
                    "name": "Search and link organization (optional)",
                    "tool_name": "search_organizations",
                    "description": "If org_name is provided, search Organization table to find a match. Use first() result to link the contact.",
                    "context": {
                        "procedure": [
                            "1. IF org_name is provided: query Organization WHERE tenant_id AND name ILIKE '%{org_name}%' LIMIT 1",
                            "2. IF found: store org.id for linking",
                            "3. IF not found or not provided: proceed without org link",
                        ],
                        "tool_priority": ["search_organizations"],
                        "required_info": [],
                        "optional_info": ["org_name"],
                        "db_table": "organizations",
                        "db_filter": "name ILIKE '%{org_name}%' LIMIT 1",
                        "expected_output": "org_id or None",
                        "model_hint": "fast",
                    },
                },
                {
                    "name": "Insert contact record",
                    "tool_name": "create_contact",
                    "description": "Create the contact with all provided fields. Defaults: status=ACTIVE, source='manual'.",
                    "context": {
                        "procedure": [
                            "1. Create Contact(tenant_id, first_name, last_name, email=email or '', phone=phone or '', organization_id=org_id or None, created_by=user_email)",
                            "2. db.add() + db.commit()",
                            "3. add_tool_step('create contact')",
                            "4. Return: '✅ Contact créé : **{first} {last}** ({email})'",
                        ],
                        "tool_priority": ["create_contact"],
                        "required_info": ["contact_first", "contact_last"],
                        "optional_info": ["email", "phone", "org_id"],
                        "db_table": "contacts",
                        "db_operation": "INSERT",
                        "expected_output": "✅ Contact créé : **{name}** ({email})",
                        "response_format": "✅ Contact créé : **{first} {last}** ({email})",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "search_entity",
            "workflow_key": "search_entity",
            "description": "Search for organizations, contacts, or opportunities by name. Determines entity type from user message, runs the query, and emits a UI search action to show results.",
            "category": "search",
            "trigger_phrases": [
                "cherche", "trouve", "search", "find", "où est",
                "montre-moi les", "show me", "look up", "recherche",
            ],
            "tasks": [
                {
                    "name": "Determine entity type and run search",
                    "tool_name": "search_organizations",
                    "description": "Detect whether user wants org, contact, or opp search. Default to organization if ambiguous. Run ilike query, emit UI search action.",
                    "context": {
                        "procedure": [
                            "1. Determine entity_type from entities or default to 'organization'",
                            "2. Build query = search_query or org_name or ''",
                            "3. IF entity_type == 'organization':",
                            "   a. Query Organization WHERE tenant_id AND name ILIKE '%{query}%' LIMIT 5",
                            "   b. emit_action('search_entity', entity='organization', page='organizations', name=query)",
                            "   c. emit_action('ui_update_input', text=query, submit=True)",
                            "   d. add_tool_step('search organizations')",
                            "4. IF entity_type == 'contact':",
                            "   a. Query ALL contacts for tenant, then filter in-memory by name/email containing query",
                            "   b. emit_action('search_entity', entity='contact', page='contacts', name=query)",
                            "   c. add_tool_step('search contacts')",
                            "5. Return '{n} résultat(s) trouvé(s) pour « {query} ».' or 'Aucun résultat'",
                        ],
                        "tool_priority": ["search_organizations", "search_contacts"],
                        "required_info": ["search_query"],
                        "optional_info": ["entity_type"],
                        "db_tables": ["organizations", "contacts"],
                        "db_filter": "name ILIKE '%{query}%' LIMIT 5",
                        "expected_output": "{n} résultat(s) trouvé(s) pour « {query} ».",
                        "response_format": "{n} résultat(s) trouvé(s) pour « {query} ».",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "navigate",
            "workflow_key": "navigate",
            "description": "Navigate the user to a CRM page. No database query — just maps the page name to a route and emits a navigation action.",
            "category": "navigation",
            "trigger_phrases": [
                "va sur", "go to", "montre-moi", "navigate to", "ouvre",
                "amène-moi", "take me to", "page", "aller à",
            ],
            "tasks": [
                {
                    "name": "Emit navigation action",
                    "tool_name": "navigate_to",
                    "description": "Map the requested page to a valid CRM route and emit navigate action. Valid pages: dashboard, organizations, contacts, opportunities, quotes, activities, settings, settings/team, knowledge-base.",
                    "context": {
                        "procedure": [
                            "1. Extract page from entities (e.g. 'dashboard', 'contacts', 'opportunities')",
                            "2. Map synonyms: 'accueil'→'dashboard', 'orgs'→'organizations', etc.",
                            "3. emit_action('navigate', page=target)",
                            "4. Return 'Navigation vers {target}.'",
                        ],
                        "tool_priority": ["navigate_to"],
                        "required_info": ["page"],
                        "valid_pages": ["dashboard", "organizations", "contacts", "opportunities", "quotes", "activities", "settings", "settings/team", "knowledge-base"],
                        "expected_output": "Navigation vers {page}.",
                        "response_format": "Navigation vers {page}.",
                        "model_hint": "fast",
                    },
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
#  DOMAIN 2: CRM ANALYTICS
# ═══════════════════════════════════════════════════════════════

CRM_ANALYTICS = {
    "name": "CRM Analytics",
    "description": "Pipeline statistics, deal analysis, and sales performance metrics. All read-only queries against the Opportunity table — no data is modified.",
    "icon": "fa-solid fa-chart-line",
    "intents": [
        {
            "name": "get_pipeline",
            "workflow_key": "get_pipeline",
            "description": "Pipeline statistics grouped by stage. Counts opportunities and sums amounts per stage. Returns a text breakdown, no bob_display card.",
            "category": "analytics",
            "trigger_phrases": [
                "pipeline", "stats du pipeline", "pipeline stats",
                "sales pipeline", "mes ventes", "show pipeline",
            ],
            "tasks": [
                {
                    "name": "Aggregate pipeline by stage",
                    "tool_name": "get_pipeline_stats",
                    "description": "GROUP BY stage on Opportunity, count and sum amounts. Format as markdown list.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT stage, COUNT(id), COALESCE(SUM(amount), 0) FROM opportunities WHERE tenant_id=current GROUP BY stage",
                            "2. Build text: '📊 **Pipeline de ventes** :'",
                            "3. For each stage: '- **{stage}** : {count} opp. — {value}$'",
                            "4. Add total: '**Total** : {total_count} opportunités — {total_value}$'",
                            "5. IF empty: 'Le pipeline est vide pour le moment.'",
                        ],
                        "tool_priority": ["get_pipeline_stats"],
                        "required_info": [],
                        "db_table": "opportunities",
                        "db_operation": "SELECT + GROUP BY stage",
                        "db_aggregations": ["COUNT(id)", "SUM(amount)"],
                        "expected_output": "📊 **Pipeline de ventes** :\n- **QUALIFICATION** : 3 opp. — 15000$\n...\n**Total** : 10 opportunités — 50000$",
                        "response_format": "📊 **Pipeline de ventes** :\n- **{stage}** : {count} opp. — {value}$\n\n**Total** : {total} opportunités — {total_value}$",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "top_opportunities",
            "workflow_key": "top_opportunities",
            "description": "Top 5 opportunities sorted by amount descending. Displayed as a bob_display list with trophy icon.",
            "category": "analytics",
            "trigger_phrases": [
                "meilleures opportunités", "best deals", "top deals",
                "top 5", "biggest deals", "plus gros deals",
            ],
            "tasks": [
                {
                    "name": "Query and display top 5 opps",
                    "tool_name": "get_pipeline_stats",
                    "description": "SELECT top 5 opportunities by amount DESC, emit bob_display list.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT * FROM opportunities WHERE tenant_id=current AND amount IS NOT NULL ORDER BY amount DESC LIMIT 5",
                            "2. For each opp, build item: {id, number, title=name, subtitle='{amount}$', tags=[{label=stage, icon=stage_icon}], route='/opportunities'}",
                            "3. emit_action('bob_display', display_type='list', title='Top 5 Opportunités', subtitle='Triées par montant', icon='fa-solid fa-trophy', items=items)",
                            "4. add_tool_step('list top opportunities')",
                            "5. Return 'Voici vos **{n} meilleures opportunités** par montant :'",
                        ],
                        "tool_priority": ["get_pipeline_stats"],
                        "required_info": [],
                        "db_table": "opportunities",
                        "db_filter": "amount IS NOT NULL",
                        "db_order": "amount DESC",
                        "db_limit": 5,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-trophy",
                        "expected_output": "bob_display list card + text summary",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "closing_this_month",
            "workflow_key": "closing_this_month",
            "description": "Opportunities with close_date in the current month. Displayed as a bob_display list with calendar icon.",
            "category": "analytics",
            "trigger_phrases": [
                "closing this month", "à closer ce mois", "deals du mois",
                "opportunités ce mois", "what's closing", "à fermer",
            ],
            "tasks": [
                {
                    "name": "Filter opps closing this month",
                    "tool_name": "get_pipeline_stats",
                    "description": "Filter opportunities where close_date is between today and end of current month.",
                    "context": {
                        "procedure": [
                            "1. Calculate month_end = last day of current month",
                            "2. Query: SELECT * FROM opportunities WHERE tenant_id=current AND close_date >= now AND close_date <= month_end ORDER BY close_date LIMIT 10",
                            "3. Build items with tags showing stage + close_date",
                            "4. emit_action('bob_display', display_type='list', title='À closer ce mois', subtitle='{month} {year}', icon='fa-solid fa-calendar-check', items=items)",
                            "5. add_tool_step('closing this month')",
                            "6. Return '**{n}** opportunité(s) à conclure ce mois-ci.'",
                        ],
                        "tool_priority": ["get_pipeline_stats"],
                        "required_info": [],
                        "db_table": "opportunities",
                        "db_filter": "close_date BETWEEN now() AND end_of_month()",
                        "db_order": "close_date ASC",
                        "db_limit": 10,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-calendar-check",
                        "expected_output": "bob_display list + '**{n}** opportunité(s) à conclure ce mois-ci.'",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "stale_deals",
            "workflow_key": "stale_deals",
            "description": "Deals not updated in 30+ days, excluding closed ones. Displayed as bob_display list with hourglass icon and warning styling.",
            "category": "analytics",
            "trigger_phrases": [
                "deals stagnants", "stale deals", "deals inactifs",
                "deals bloqués", "stuck deals", "inactive deals",
            ],
            "tasks": [
                {
                    "name": "Find deals inactive 30+ days",
                    "tool_name": "get_pipeline_stats",
                    "description": "Filter opportunities where updated_at < 30 days ago and stage is NOT CLOSED_WON or CLOSED_LOST.",
                    "context": {
                        "procedure": [
                            "1. threshold = now() - 30 days",
                            "2. Query: SELECT * FROM opportunities WHERE tenant_id=current AND updated_at < threshold AND stage NOT IN ('CLOSED_WON', 'CLOSED_LOST') ORDER BY updated_at LIMIT 10",
                            "3. For each: calculate days_stale = (now - updated_at).days",
                            "4. Build items with tags: [{label=stage}, {label='{days}j stagnant', icon='fa-solid fa-clock', color='#ef4444'}]",
                            "5. emit_action('bob_display', display_type='list', title='Deals stagnants', subtitle='+30 jours sans mouvement', icon='fa-solid fa-hourglass-half', items=items)",
                            "6. add_tool_step('stale deals')",
                            "7. Return '⚠️ **{n}** deal(s) stagnant(s) depuis plus de 30 jours.' or 'Aucun deal stagnant — bravo ! 🎉'",
                        ],
                        "tool_priority": ["get_pipeline_stats"],
                        "required_info": [],
                        "db_table": "opportunities",
                        "thresholds": {"stale_days": 30},
                        "db_filter": "updated_at < (now - 30d) AND stage NOT IN (CLOSED_WON, CLOSED_LOST)",
                        "db_limit": 10,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-hourglass-half",
                        "expected_output": "⚠️ **{n}** deal(s) stagnant(s) depuis plus de 30 jours.",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "pipeline_value",
            "workflow_key": "pipeline_value",
            "description": "Pipeline value breakdown by stage. Displayed as bob_display stats card with pie chart icon.",
            "category": "analytics",
            "trigger_phrases": [
                "valeur du pipeline", "pipeline value", "combien dans le pipeline",
                "revenue pipeline", "montant total", "deal amounts",
            ],
            "tasks": [
                {
                    "name": "Aggregate value by stage",
                    "tool_name": "get_pipeline_stats",
                    "description": "GROUP BY stage, SUM amount. Display as stats card with value per stage.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT stage, COUNT(id), COALESCE(SUM(amount), 0) FROM opportunities WHERE tenant_id=current GROUP BY stage",
                            "2. Build stats array: [{label=stage, value='{value}$', sub='{count} deals'}]",
                            "3. emit_action('bob_display', display_type='stats', title='Valeur du Pipeline', subtitle='Répartition par étape', icon='fa-solid fa-chart-pie', stats=stats)",
                            "4. add_tool_step('pipeline value')",
                            "5. Return '📊 Pipeline : **{total_count}** deals — **{total_value}$**'",
                        ],
                        "tool_priority": ["get_pipeline_stats"],
                        "required_info": [],
                        "db_table": "opportunities",
                        "db_operation": "SELECT + GROUP BY stage",
                        "db_aggregations": ["COUNT(id)", "SUM(amount)"],
                        "display_type": "stats",
                        "display_icon": "fa-solid fa-chart-pie",
                        "expected_output": "📊 Pipeline : **{n}** deals — **{total}$**",
                        "model_hint": "fast",
                    },
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
#  DOMAIN 3: CRM INTELLIGENCE
# ═══════════════════════════════════════════════════════════════

CRM_INTELLIGENCE = {
    "name": "CRM Intelligence",
    "description": "Contact and account insights — find dormant contacts, data quality issues, account activity patterns, and industry breakdowns. All read-only queries.",
    "icon": "fa-solid fa-brain",
    "intents": [
        {
            "name": "dormant_contacts",
            "workflow_key": "dormant_contacts",
            "description": "Find contacts not updated in 5+ months (150 days). Useful for re-engagement campaigns.",
            "category": "intelligence",
            "trigger_phrases": [
                "contacts dormants", "dormant contacts", "contacts inactifs",
                "qui n'a pas été contacté", "inactive contacts", "à relancer",
            ],
            "tasks": [
                {
                    "name": "Query contacts inactive 150+ days",
                    "tool_name": "search_contacts",
                    "description": "Filter contacts where updated_at < 150 days ago. Display as bob_display list with user-clock icon.",
                    "context": {
                        "procedure": [
                            "1. threshold = now() - 150 days",
                            "2. Query: SELECT * FROM contacts WHERE tenant_id=current AND updated_at < threshold ORDER BY updated_at LIMIT 10",
                            "3. For each: days_dormant = (now - updated_at).days",
                            "4. Build items: tags=[{label='{days}j inactif', icon='fa-solid fa-clock', color='#f59e0b'}]",
                            "5. emit_action('bob_display', display_type='list', title='Contacts dormants', subtitle='Pas contactés depuis 5+ mois', icon='fa-solid fa-user-clock', items=items)",
                            "6. add_tool_step('dormant contacts')",
                            "7. Return '📞 **{n}** contact(s) à relancer — inactifs depuis plus de 5 mois.' or 'Tous vos contacts ont été contactés récemment ! ✅'",
                        ],
                        "tool_priority": ["search_contacts"],
                        "required_info": [],
                        "db_table": "contacts",
                        "thresholds": {"dormant_days": 150},
                        "db_filter": "updated_at < (now - 150d)",
                        "db_limit": 10,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-user-clock",
                        "expected_output": "📞 **{n}** contact(s) à relancer",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "recent_contacts",
            "workflow_key": "recent_contacts",
            "description": "List the 10 most recently added contacts, sorted by created_at DESC.",
            "category": "intelligence",
            "trigger_phrases": [
                "contacts récents", "recent contacts", "derniers contacts",
                "nouveaux contacts", "new contacts", "recently added",
            ],
            "tasks": [
                {
                    "name": "List last 10 contacts by creation date",
                    "tool_name": "search_contacts",
                    "description": "Simple ORDER BY created_at DESC LIMIT 10. Display as bob_display list.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT * FROM contacts WHERE tenant_id=current ORDER BY created_at DESC LIMIT 10",
                            "2. Build items: title='{first} {last}', subtitle=email or phone, tags=[org_name if linked]",
                            "3. emit_action('bob_display', display_type='list', title='Contacts récents', subtitle='Derniers ajoutés', icon='fa-solid fa-user-plus', items=items)",
                            "4. add_tool_step('recent contacts')",
                            "5. Return 'Voici les **{n} derniers contacts** ajoutés :'",
                        ],
                        "tool_priority": ["search_contacts"],
                        "required_info": [],
                        "db_table": "contacts",
                        "db_order": "created_at DESC",
                        "db_limit": 10,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-user-plus",
                        "expected_output": "bob_display list of recent contacts",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "contacts_no_email",
            "workflow_key": "contacts_no_email",
            "description": "Find contacts missing an email address — data quality check.",
            "category": "intelligence",
            "trigger_phrases": [
                "contacts sans email", "contacts no email", "email manquant",
                "missing email", "données incomplètes", "incomplete data",
            ],
            "tasks": [
                {
                    "name": "Filter contacts with null/empty email",
                    "tool_name": "search_contacts",
                    "description": "Query contacts where email IS NULL or email = ''. Display with warning icon.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT * FROM contacts WHERE tenant_id=current AND (email IS NULL OR email = '') LIMIT 10",
                            "2. Build items: tags=[{label='Email manquant', icon='fa-solid fa-exclamation-triangle', color='#ef4444'}]",
                            "3. emit_action('bob_display', display_type='list', title='Contacts sans email', subtitle='Données incomplètes', icon='fa-solid fa-at', items=items)",
                            "4. add_tool_step('contacts no email')",
                            "5. Return '⚠️ **{n}** contact(s) sans adresse email.' or 'Tous vos contacts ont un email ! ✅'",
                        ],
                        "tool_priority": ["search_contacts"],
                        "required_info": [],
                        "db_table": "contacts",
                        "db_filter": "email IS NULL OR email = ''",
                        "db_limit": 10,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-at",
                        "expected_output": "⚠️ **{n}** contact(s) sans adresse email.",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "accounts_no_opp",
            "workflow_key": "accounts_no_opp",
            "description": "Organizations that have zero opportunities — untapped potential.",
            "category": "intelligence",
            "trigger_phrases": [
                "comptes sans opportunité", "accounts no opp", "orgs without deals",
                "potentiel inexploité", "no deals", "untapped accounts",
            ],
            "tasks": [
                {
                    "name": "Find orgs without any opportunities",
                    "tool_name": "search_organizations",
                    "description": "Use a subquery to find org IDs that have opps, then filter for orgs NOT in that set.",
                    "context": {
                        "procedure": [
                            "1. Subquery: SELECT DISTINCT organization_id FROM opportunities WHERE tenant_id=current",
                            "2. Query: SELECT * FROM organizations WHERE tenant_id=current AND id NOT IN (subquery) LIMIT 10",
                            "3. Build items: tags=[{label=industry}], route='/organizations'",
                            "4. emit_action('bob_display', display_type='list', title='Comptes sans opportunité', subtitle='Potentiel inexploité', icon='fa-solid fa-building-circle-exclamation', items=items)",
                            "5. add_tool_step('accounts without opportunity')",
                            "6. Return '📋 **{n}** compte(s) sans aucune opportunité — du potentiel inexploité !' or 'Tous vos comptes ont au moins une opportunité ! ✅'",
                        ],
                        "tool_priority": ["search_organizations"],
                        "required_info": [],
                        "db_tables": ["organizations", "opportunities"],
                        "db_operation": "LEFT JOIN / NOT IN subquery",
                        "db_limit": 10,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-building-circle-exclamation",
                        "expected_output": "📋 **{n}** compte(s) sans aucune opportunité",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "most_active_accounts",
            "workflow_key": "most_active_accounts",
            "description": "Top 5 organizations ranked by opportunity count. Uses JOIN + GROUP BY.",
            "category": "intelligence",
            "trigger_phrases": [
                "comptes actifs", "most active accounts", "top accounts",
                "meilleurs comptes", "best accounts", "comptes les plus actifs",
            ],
            "tasks": [
                {
                    "name": "Rank orgs by opportunity count",
                    "tool_name": "search_organizations",
                    "description": "JOIN organizations with opportunities, GROUP BY org, ORDER BY count DESC. Display as bob_display list with fire icon.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT org.id, org.name, org.industry, COUNT(opp.id) as opp_count FROM organizations org JOIN opportunities opp ON opp.organization_id = org.id WHERE org.tenant_id=current GROUP BY org.id, org.name, org.industry ORDER BY opp_count DESC LIMIT 5",
                            "2. Build items: subtitle='{count} opportunités', tags=[{label=industry}]",
                            "3. emit_action('bob_display', display_type='list', title='Comptes les plus actifs', subtitle='Par nombre d\\'opportunités', icon='fa-solid fa-fire', items=items)",
                            "4. add_tool_step('most active accounts')",
                            "5. Return '🔥 Voici vos **{n} comptes les plus actifs** :'",
                        ],
                        "tool_priority": ["search_organizations"],
                        "required_info": [],
                        "db_tables": ["organizations", "opportunities"],
                        "db_operation": "JOIN + GROUP BY + ORDER BY COUNT DESC",
                        "db_limit": 5,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-fire",
                        "expected_output": "🔥 Voici vos **{n} comptes les plus actifs** :",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "accounts_by_industry",
            "workflow_key": "accounts_by_industry",
            "description": "Account breakdown grouped by industry field. Displayed as bob_display stats card.",
            "category": "intelligence",
            "trigger_phrases": [
                "comptes par industrie", "accounts by industry", "répartition industrie",
                "industry breakdown", "secteurs d'activité", "by sector",
            ],
            "tasks": [
                {
                    "name": "Group orgs by industry and count",
                    "tool_name": "search_organizations",
                    "description": "GROUP BY industry, COUNT per group. Display as stats card with bar chart icon.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT industry, COUNT(id) FROM organizations WHERE tenant_id=current AND industry IS NOT NULL AND industry != '' GROUP BY industry ORDER BY COUNT(id) DESC",
                            "2. Build stats: [{label=industry, value='{count}', sub='comptes'}]",
                            "3. emit_action('bob_display', display_type='stats', title='Comptes par industrie', subtitle='Répartition', icon='fa-solid fa-chart-bar', stats=stats)",
                            "4. add_tool_step('accounts by industry')",
                            "5. Return '📊 Répartition de vos comptes par industrie ({n} industries) :'",
                        ],
                        "tool_priority": ["search_organizations"],
                        "required_info": [],
                        "db_table": "organizations",
                        "db_operation": "GROUP BY industry + COUNT",
                        "db_filter": "industry IS NOT NULL AND industry != ''",
                        "display_type": "stats",
                        "display_icon": "fa-solid fa-chart-bar",
                        "expected_output": "📊 Répartition de vos comptes par industrie ({n} industries) :",
                        "model_hint": "fast",
                    },
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
#  DOMAIN 4: PRODUCTS & OVERVIEW
# ═══════════════════════════════════════════════════════════════

PRODUCTS_OVERVIEW = {
    "name": "Products & Overview",
    "description": "Product catalog listing and daily summary dashboard. Quick access to catalog and morning standup data.",
    "icon": "fa-solid fa-box",
    "intents": [
        {
            "name": "list_products",
            "workflow_key": "list_products",
            "description": "List all products in the catalog with name, price, SKU, and category. Displayed as bob_display list.",
            "category": "catalog",
            "trigger_phrases": [
                "produits", "catalogue", "products", "list products",
                "show catalog", "voir les produits", "product list",
            ],
            "tasks": [
                {
                    "name": "Query and display product catalog",
                    "tool_name": "get_pipeline_stats",
                    "description": "Query Product table ordered by name. Display each product with price and category tags.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT * FROM products WHERE tenant_id=current ORDER BY name LIMIT 15",
                            "2. Build items: title=name, subtitle='{price}$', tags=[{label=category}, {label=sku}]",
                            "3. emit_action('bob_display', display_type='list', title='Catalogue Produits', subtitle='{n} produits', icon='fa-solid fa-box', items=items)",
                            "4. add_tool_step('list products')",
                            "5. Return 'Voici les **{n} produits** du catalogue :' or 'Aucun produit dans le catalogue.'",
                        ],
                        "tool_priority": [],
                        "required_info": [],
                        "db_table": "products",
                        "db_order": "name ASC",
                        "db_limit": 15,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-box",
                        "expected_output": "bob_display list of products",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "daily_summary",
            "workflow_key": "daily_summary",
            "description": "Complete daily summary with pipeline totals, stale deals count, contact count, and org count. Displayed as a stats card — perfect for morning standup.",
            "category": "overview",
            "trigger_phrases": [
                "résumé", "daily summary", "bonjour", "overview",
                "quoi de neuf", "morning briefing", "standup", "comment va mon pipeline",
            ],
            "tasks": [
                {
                    "name": "Compile multi-table daily stats",
                    "tool_name": "get_pipeline_stats",
                    "description": "Run 4 queries: open opps (count + sum), stale opps count, total contacts, total orgs. Display as stats card with sun icon.",
                    "context": {
                        "procedure": [
                            "1. Query open opps: SELECT COUNT(id), COALESCE(SUM(amount), 0) FROM opportunities WHERE tenant_id=current AND stage NOT IN ('CLOSED_WON', 'CLOSED_LOST')",
                            "2. Query stale: SELECT COUNT(id) FROM opportunities WHERE tenant_id=current AND updated_at < (now - 30d) AND stage NOT IN ('CLOSED_WON', 'CLOSED_LOST')",
                            "3. Query contacts: SELECT COUNT(id) FROM contacts WHERE tenant_id=current",
                            "4. Query orgs: SELECT COUNT(id) FROM organizations WHERE tenant_id=current",
                            "5. Build stats: [{label='Pipeline', value='{total_value}$', sub='{open_count} deals ouverts'}, {label='Stagnants', value='{stale}', sub='30+ jours'}, {label='Contacts', value='{contacts}'}, {label='Organisations', value='{orgs}'}]",
                            "6. emit_action('bob_display', display_type='stats', title='Résumé de votre journée', subtitle='{date}', icon='fa-solid fa-sun', stats=stats)",
                            "7. add_tool_step('daily summary')",
                            "8. Return '☀️ **Bonjour !** Votre pipeline : **{value}$** ({n} deals ouverts, ⚠️ {stale} stagnants)'",
                        ],
                        "tool_priority": ["get_pipeline_stats"],
                        "required_info": [],
                        "db_tables": ["opportunities", "contacts", "organizations"],
                        "db_operation": "Multiple COUNT/SUM queries",
                        "display_type": "stats",
                        "display_icon": "fa-solid fa-sun",
                        "expected_output": "☀️ **Bonjour !** stats card + pipeline summary",
                        "response_format": "☀️ **Bonjour !** Votre pipeline : **{value}$** ({n} deals ouverts, ⚠️ {stale} stagnants)",
                        "model_hint": "fast",
                    },
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
#  DOMAIN 5: ACTIVITIES
# ═══════════════════════════════════════════════════════════════

ACTIVITIES = {
    "name": "Activities",
    "description": "Activity management — create, track, and review calls, emails, meetings, tasks, and notes. Linked to contacts and organizations.",
    "icon": "fa-solid fa-calendar-check",
    "intents": [
        {
            "name": "create_activity",
            "workflow_key": "create_activity",
            "description": "Create a new activity of type CALL, EMAIL, MEETING, TASK, or NOTE. Detects type from user message keywords, finds linked contact if mentioned.",
            "category": "activities",
            "trigger_phrases": [
                "note un appel", "log a call", "crée un rappel", "ajoute une activité",
                "meeting", "réunion", "note", "schedule a meeting", "log email",
                "add a task", "créer une tâche", "planifier",
            ],
            "tasks": [
                {
                    "name": "Detect activity type from message",
                    "tool_name": None,
                    "description": "Analyze user message for type keywords. Map: appel/call→CALL, email/courriel→EMAIL, meeting/réunion→MEETING, tâche/task/rappel→TASK, note→NOTE. Default to NOTE.",
                    "context": {
                        "procedure": [
                            "1. Scan user_message for keywords:",
                            "   - 'appel', 'call', 'téléphone' → CALL",
                            "   - 'email', 'courriel', 'mail' → EMAIL",
                            "   - 'meeting', 'réunion', 'rencontre' → MEETING",
                            "   - 'tâche', 'task', 'rappel', 'reminder' → TASK",
                            "   - 'note' → NOTE",
                            "2. Default to NOTE if no keyword matched",
                            "3. Store activity_type in workflow state",
                        ],
                        "tool_priority": [],
                        "required_info": ["user_message"],
                        "keyword_map": {
                            "CALL": ["appel", "call", "téléphone", "phone"],
                            "EMAIL": ["email", "courriel", "mail"],
                            "MEETING": ["meeting", "réunion", "rencontre"],
                            "TASK": ["tâche", "task", "rappel", "reminder"],
                            "NOTE": ["note"],
                        },
                        "default_type": "NOTE",
                        "expected_output": "activity_type stored in state",
                        "model_hint": "fast",
                    },
                },
                {
                    "name": "Find contact and create activity",
                    "tool_name": "get_recent_activities",
                    "description": "If contact name is provided, search contacts table. Build subject line from context. Create Activity record with type, subject, status=PENDING, due_date=now.",
                    "context": {
                        "procedure": [
                            "1. IF contact_first provided: query Contact WHERE tenant_id AND first_name ILIKE '%{contact_first}%' LIMIT 1",
                            "2. Build subject: '{type_label} — {contact_name}' or '{type_label} — {user_message[:50]}'",
                            "3. Create Activity(tenant_id, subject, activity_type, status='PENDING', due_date=now, contact_id=contact.id or None, created_by=user_email)",
                            "4. db.add() + db.commit()",
                            "5. add_tool_step('create activity')",
                            "6. Return '✅ {type_label} créé : **{subject}** — lié au contact **{contact_name}**'",
                        ],
                        "tool_priority": ["get_recent_activities"],
                        "required_info": ["activity_type"],
                        "optional_info": ["contact_first", "contact_last"],
                        "db_tables": ["contacts", "activities"],
                        "db_operation": "SELECT contact + INSERT activity",
                        "expected_output": "✅ {type_label} créé : **{subject}**",
                        "response_format": "✅ {type} créé : **{subject}** — lié au contact **{contact}**",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "today_activities",
            "workflow_key": "today_activities",
            "description": "List activities due today. Shows completed vs pending count. Displayed as bob_display list with calendar icon.",
            "category": "activities",
            "trigger_phrases": [
                "activités du jour", "today activities", "quoi de prévu",
                "agenda", "my schedule", "qu'est-ce que j'ai aujourd'hui",
            ],
            "tasks": [
                {
                    "name": "Query and display today's activities",
                    "tool_name": "get_recent_activities",
                    "description": "Filter activities where due_date is today. Split into completed/pending counts. Display as list with status icons.",
                    "context": {
                        "procedure": [
                            "1. today_start = start of today, today_end = end of today",
                            "2. Query: SELECT * FROM activities WHERE tenant_id=current AND due_date BETWEEN today_start AND today_end ORDER BY due_date LIMIT 15",
                            "3. Count completed (status=COMPLETED) vs pending (others)",
                            "4. Build items: tags=[{label=type, icon=type_icon}, {label=status, color=status_color}]",
                            "5. emit_action('bob_display', display_type='list', title='Activités du jour', subtitle='{date} — {completed} complétées, {pending} restantes', icon='fa-solid fa-calendar-day', items=items)",
                            "6. add_tool_step('today activities')",
                            "7. Return '📅 **{n}** activité(s) aujourd'hui — {completed} complétées, {pending} restantes.' or '📭 Aucune activité prévue pour aujourd'hui.'",
                        ],
                        "tool_priority": ["get_recent_activities"],
                        "required_info": [],
                        "db_table": "activities",
                        "db_filter": "due_date BETWEEN today_start AND today_end",
                        "db_order": "due_date ASC",
                        "db_limit": 15,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-calendar-day",
                        "expected_output": "📅 **{n}** activité(s) aujourd'hui",
                        "model_hint": "fast",
                    },
                },
            ],
        },
        {
            "name": "overdue_activities",
            "workflow_key": "overdue_activities",
            "description": "Activities past due date with status PENDING or IN_PROGRESS. Displayed as bob_display list with warning triangle icon.",
            "category": "activities",
            "trigger_phrases": [
                "rappels en retard", "overdue activities", "activités manquées",
                "late tasks", "en retard", "overdue reminders",
            ],
            "tasks": [
                {
                    "name": "Find overdue pending/in-progress activities",
                    "tool_name": "get_recent_activities",
                    "description": "Filter activities where due_date < now and status in (PENDING, IN_PROGRESS). Calculate days overdue.",
                    "context": {
                        "procedure": [
                            "1. Query: SELECT * FROM activities WHERE tenant_id=current AND due_date < now() AND status IN ('PENDING', 'IN_PROGRESS') ORDER BY due_date LIMIT 10",
                            "2. For each: days_overdue = (now - due_date).days",
                            "3. Build items: tags=[{label=type, icon=type_icon}, {label='{days}j en retard', icon='fa-solid fa-clock', color='#ef4444'}]",
                            "4. emit_action('bob_display', display_type='list', title='Rappels en retard', subtitle='{n} activité(s) en souffrance', icon='fa-solid fa-triangle-exclamation', items=items)",
                            "5. add_tool_step('overdue activities')",
                            "6. Return '⚠️ **{n}** activité(s) en retard — à traiter rapidement !' or '✅ Aucun rappel en retard — tout est à jour !'",
                        ],
                        "tool_priority": ["get_recent_activities"],
                        "required_info": [],
                        "db_table": "activities",
                        "db_filter": "due_date < now() AND status IN (PENDING, IN_PROGRESS)",
                        "db_order": "due_date ASC",
                        "db_limit": 10,
                        "display_type": "list",
                        "display_icon": "fa-solid fa-triangle-exclamation",
                        "expected_output": "⚠️ **{n}** activité(s) en retard",
                        "model_hint": "fast",
                    },
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
#  DOMAIN 6: DATA ENRICHMENT (pipeline visibility)
# ═══════════════════════════════════════════════════════════════

DATA_ENRICHMENT = {
    "name": "Data Enrichment",
    "description": "LangGraph pipeline that enriches organization data by scraping websites and extracting structured information. Runtime is code-driven — BCC provides visibility into what the pipeline does.",
    "icon": "fa-solid fa-magnifying-glass-plus",
    "intents": [
        {
            "name": "enrich_organization",
            "workflow_key": None,
            "pipeline_key": "enrichment_graph",
            "description": "Scrape an organization's website and extract structured profile data (description, employees, revenue, social links). Runs as an async LangGraph pipeline: scrape → extract → update org.",
            "category": "enrichment",
            "trigger_phrases": [
                "enrichis cette organisation", "enrich this org", "scrape le site web",
                "complète les données", "enrichment", "scrape website",
                "complete org profile", "find more info",
            ],
            "tasks": [
                {
                    "name": "Scrape organization website",
                    "tool_name": None,
                    "description": "Fetch the org's website URL, scrape HTML content, clean text, and parse regex patterns for emails, phones, and social links. This is the scraper_node in the LangGraph pipeline.",
                    "context": {
                        "procedure": [
                            "1. Get org website_url from the Organization record",
                            "2. HTTP GET the website URL with timeout and user-agent headers",
                            "3. Parse HTML with BeautifulSoup, extract visible text",
                            "4. Run regex patterns to extract: emails, phone numbers, LinkedIn/Twitter/Facebook URLs",
                            "5. Store scraped_content and regex_data in pipeline state",
                        ],
                        "tool_priority": [],
                        "required_info": ["organization_id", "website_url"],
                        "pipeline_node": "scraper_node",
                        "expected_output": "scraped_content (text) + regex_data (dict with emails, phones, social_links)",
                        "model_hint": "n/a — code-driven",
                    },
                },
                {
                    "name": "Extract structured data via LLM",
                    "tool_name": None,
                    "description": "Send the scraped text to a Groq LLM to extract structured fields: description, employee_count, revenue_range, services, founded_year. Merge with regex data and update the org record.",
                    "context": {
                        "procedure": [
                            "1. Build extraction prompt with scraped_content",
                            "2. Call Groq LLM in JSON mode to extract: description, employee_count, revenue, services[], technologies[], founded_year",
                            "3. Merge LLM output with regex_data (emails, phones, social links)",
                            "4. UPDATE Organization SET description, employee_count, revenue, website, linkedin_url, etc.",
                            "5. Create BccProfileEntry records for enriched sections",
                        ],
                        "tool_priority": [],
                        "required_info": ["scraped_content", "regex_data"],
                        "pipeline_node": "extraction_node",
                        "llm_model": "groq/llama-3.3-70b",
                        "extracted_fields": ["description", "employee_count", "revenue", "services", "technologies", "founded_year", "linkedin_url", "social_links"],
                        "expected_output": "Updated organization record with enriched profile data",
                        "model_hint": "n/a — code-driven",
                    },
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
#  DOMAIN 7: KNOWLEDGE RETRIEVAL (pipeline visibility)
# ═══════════════════════════════════════════════════════════════

KNOWLEDGE_RETRIEVAL = {
    "name": "Knowledge Retrieval",
    "description": "RAG LangGraph pipeline — classify user query, retrieve relevant chunks from knowledge base, synthesize answer with citations. Runtime is code-driven — BCC provides visibility.",
    "icon": "fa-solid fa-book-open",
    "intents": [
        {
            "name": "rag_knowledge_query",
            "workflow_key": None,
            "pipeline_key": "rag_graph",
            "description": "Answer user questions using the knowledge base with retrieval-augmented generation. Flow: classify intent → check if retrieval needed → retrieve chunks → filter by permissions → synthesize with citations.",
            "category": "rag",
            "trigger_phrases": [
                "cherche dans la base de connaissance", "knowledge base", "documentation",
                "comment faire", "how to", "procédure", "look up in KB",
                "what does the doc say", "aide-moi avec",
            ],
            "tasks": [
                {
                    "name": "Classify query intent",
                    "tool_name": None,
                    "description": "Classify the user query as knowledge (needs KB retrieval), data (needs CRM lookup), action (needs CRM action), or chat (general). Determines whether to run retrieval.",
                    "context": {
                        "procedure": [
                            "1. Send query to Groq LLM with classification prompt",
                            "2. Prompt asks to classify as: knowledge | data | action | chat",
                            "3. Also determine needs_retrieval (boolean)",
                            "4. Return JSON: {category, needs_retrieval}",
                            "5. IF needs_retrieval=false: skip to direct_answer node",
                        ],
                        "tool_priority": [],
                        "required_info": ["query"],
                        "pipeline_node": "classify_intent_node",
                        "classification_categories": ["knowledge", "data", "action", "chat"],
                        "expected_output": "{category: 'knowledge', needs_retrieval: true}",
                        "model_hint": "n/a — code-driven",
                    },
                },
                {
                    "name": "Retrieve relevant knowledge chunks",
                    "tool_name": None,
                    "description": "Query the vector store for the top-k most relevant chunks matching the user query. Filter by tenant_id and user permissions/module access.",
                    "context": {
                        "procedure": [
                            "1. Generate embedding for the user query",
                            "2. Search vector store for top-k nearest chunks (k=5)",
                            "3. Filter results by tenant_id",
                            "4. Filter by user_roles and user_modules (authorization)",
                            "5. Return list of {chunk_id, content, source, score}",
                        ],
                        "tool_priority": [],
                        "required_info": ["query", "tenant_id", "user_roles", "user_modules"],
                        "pipeline_node": "retrieve_node",
                        "retrieval_config": {"top_k": 5},
                        "expected_output": "List of retrieved_chunks with content and source metadata",
                        "model_hint": "n/a — code-driven",
                    },
                },
                {
                    "name": "Synthesize answer with citations",
                    "tool_name": None,
                    "description": "Build a context window from retrieved chunks, send to LLM with synthesis prompt, generate a grounded answer with inline citation references [1], [2], etc.",
                    "context": {
                        "procedure": [
                            "1. Build context block from retrieved_chunks: 'Source [n]: {source}\\n{content}'",
                            "2. Build synthesis prompt: 'Answer the user question using ONLY the provided sources. Cite sources as [1], [2].'",
                            "3. Call Groq LLM with context + question",
                            "4. Parse response for citation markers",
                            "5. Build citations list: [{number, source, chunk_id}]",
                            "6. Store trace record for analytics",
                            "7. Return answer + citations array",
                        ],
                        "tool_priority": [],
                        "required_info": ["retrieved_chunks", "query"],
                        "pipeline_node": "synthesize_node",
                        "expected_output": "Grounded answer with [1], [2] citation references + citations metadata",
                        "model_hint": "n/a — code-driven",
                    },
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
#  DOMAIN: BOB SELF-MANAGEMENT (Deep Agent)
# ═══════════════════════════════════════════════════════════════

BOB_SELF_MANAGEMENT = {
    "name": "Bob Self-Management",
    "description": "Autonomous full-stack BCC construction via the Deep Agent system. Creates BCC domains/intents/tasks, generates OpenAI tool schemas, generates Python workflow code, validates it via code review, and hot-loads it at runtime. Uses Claude Sonnet 4.6 via OpenRouter.",
    "icon": "fa-solid fa-brain",
    "intents": [
        {
            "name": "build_bcc",
            "workflow_key": "build_bcc",
            "description": "Full-stack Deep Agent pipeline: Supervisor plans → Domain/Intent/Task builders write to DB → Tool Schema Generator creates OpenAI tool schemas → Workflow Code Generator produces Python code → Code Reviewer validates safety → Deployer writes .py files and hot-loads them into the workflow registry.",
            "category": "self_management",
            "trigger_phrases": [
                "configure Bob", "configure bob", "configurer Bob",
                "set up the BCC", "build the cognitive structure",
                "make this happen to the BCC", "enrichis le BCC",
                "crée les domaines", "build new capabilities",
                "ajoute des intents au BCC", "deep agent",
                "construis la structure cognitive", "enrichissement BCC",
                "set up domains and intents", "configure the control center",
                "ajouter au BCC", "build bcc",
                "generate workflows", "crée du code pour Bob",
                "ajoute un nouveau workflow", "create a new tool",
            ],
            "tasks": [
                {
                    "name": "Analyze instruction and plan",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. Receive user instruction (e.g. 'Add churn tracking' or 'Configure Bob for SaaS')",
                            "2. Pass to Supervisor node (Claude Sonnet 4.6 via OpenRouter)",
                            "3. Supervisor loads existing BCC domains, existing tool names, existing workflow keys",
                            "4. Supervisor generates JSON plan: domains[] → intents[] → tasks[]",
                            "5. For new intents: sets needs_workflow=true and workflow_key=intent_name",
                            "6. For tasks referencing new tools: includes tool_name not in existing BOB_TOOLS",
                        ],
                        "tool_priority": [],
                        "required_info": ["user_instruction"],
                        "expected_output": "JSON plan with domains, intents (needs_workflow flag), tasks (with context, db_table, tool_name)",
                        "model_hint": "claude-sonnet-4-6 via OpenRouter",
                    },
                },
                {
                    "name": "Build domains in database",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. For each domain in plan: check BccDomain by name + tenant_id",
                            "2. Idempotent: reuse if exists, create if new",
                            "3. Flush to get domain.id for intent linking",
                        ],
                        "db_table": "bcc_domains",
                        "db_operation": "INSERT (idempotent)",
                        "expected_output": "List of domain IDs (new or existing)",
                    },
                },
                {
                    "name": "Build intents in database",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. For each intent: find parent domain, check for existing BccIntent",
                            "2. Create BccIntent with name, trigger_phrases, workflow_key, category",
                            "3. Record needs_workflow flag for code generation phase",
                        ],
                        "db_table": "bcc_intents",
                        "db_operation": "INSERT (idempotent)",
                        "expected_output": "List of intent IDs with needs_workflow flags",
                    },
                },
                {
                    "name": "Build tasks and link to intents",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. For each task: create BccTaskTemplate with full context",
                            "2. Create BccIntentTask link: intent_id, task_template_id, sort_order, tool_name",
                            "3. Context includes: procedure, tool_priority, required_info, db_table, db_operation, expected_output",
                        ],
                        "db_table": "bcc_task_templates + bcc_intent_tasks",
                        "db_operation": "INSERT (idempotent)",
                        "expected_output": "List of task names per intent",
                    },
                },
                {
                    "name": "Generate tool schemas for new tools",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. Identify tool_names in plan that don't exist in BOB_TOOLS",
                            "2. For each new tool: call Sonnet 4.6 to generate OpenAI-format function schema",
                            "3. Schema format: {type: 'function', function: {name, description, parameters: {type: 'object', properties, required}}}",
                            "4. Store schemas in BccTaskTemplate.context['tool_schemas']",
                            "5. load_tools_from_bcc() will pick these up at runtime",
                        ],
                        "tool_priority": [],
                        "expected_output": "List of generated tool schemas stored in BCC",
                        "model_hint": "claude-sonnet-4-6 via OpenRouter",
                        "db_tables": ["organizations", "contacts", "opportunities", "activities", "products"],
                    },
                },
                {
                    "name": "Generate Python workflow code",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. For each intent with needs_workflow=true:",
                            "2. Call Sonnet 4.6 with strict template: import from workflow_engine, use @workflow() decorator",
                            "3. Function uses WorkflowContext API: ctx.db, ctx.tenant_id, ctx.complete(), ctx.emit_action(), ctx.add_tool_step()",
                            "4. ONLY allowed imports: app.domain.entities.*, sqlalchemy, datetime, json, re",
                            "5. FORBIDDEN: os, subprocess, sys, exec, eval, __import__, open(), requests, httpx",
                            "6. MUST filter all queries by ctx.tenant_id",
                            "7. Max 80 lines per function",
                        ],
                        "tool_priority": [],
                        "expected_output": "Python code string per intent, ready for review",
                        "model_hint": "claude-sonnet-4-6 via OpenRouter",
                        "safety_rules": {
                            "allowed_imports": ["app.domain.entities.*", "sqlalchemy", "datetime", "json", "re", "app.agents.workflow_engine"],
                            "forbidden": ["os", "subprocess", "sys", "exec", "eval", "__import__", "open()", "requests", "httpx"],
                            "max_lines": 80,
                            "must_filter_tenant_id": True,
                        },
                    },
                },
                {
                    "name": "Code review and safety validation",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. Static analysis: scan for forbidden patterns (os., subprocess, exec, etc.)",
                            "2. Check @workflow() decorator present, function definition exists",
                            "3. Verify tenant_id filtering in code",
                            "4. Check line count <= 120",
                            "5. LLM review (Sonnet 4.6): check SQL injection, tenant isolation, API correctness",
                            "6. If rejected: send issues back to Supervisor (max 2 revision cycles)",
                            "7. If max revisions reached: deploy BCC structure only, skip code",
                        ],
                        "tool_priority": [],
                        "expected_output": "{approved: true/false, issues: [...], summary: '...'}",
                        "model_hint": "claude-sonnet-4-6 via OpenRouter",
                    },
                },
                {
                    "name": "Deploy and hot-load workflows",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. Write approved code to app/agents/generated/{intent_name}.py",
                            "2. Call load_generated_workflows() to import via importlib",
                            "3. @workflow() decorators auto-register into _WORKFLOWS registry",
                            "4. Bob can immediately use the new workflows on next invocation",
                            "5. Files are auditable, git-diffable, and can be deleted to rollback",
                        ],
                        "tool_priority": [],
                        "expected_output": "List of deployed workflow files and loaded module names",
                        "deploy_path": "app/agents/generated/",
                    },
                },
                {
                    "name": "Report results to user",
                    "tool_name": None,
                    "context": {
                        "procedure": [
                            "1. Summarize: X domains, Y intents, Z tasks created",
                            "2. List generated tool schemas (if any)",
                            "3. List generated and deployed workflow files (if any)",
                            "4. Include code review status",
                            "5. Direct user to BCC → Cognitive Flow to see the result",
                        ],
                        "expected_output": "Confirmation message with counts, generated code status, and BCC link",
                        "response_format": "Markdown with bold counts + code deployment status",
                    },
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════
#  ASSEMBLE ALL STRUCTURES
# ═══════════════════════════════════════════════════════════════

COGNITIVE_STRUCTURE = [CRM_SALES, CRM_ANALYTICS, CRM_INTELLIGENCE, PRODUCTS_OVERVIEW, ACTIVITIES, BOB_SELF_MANAGEMENT]
PIPELINE_VISIBILITY_STRUCTURE = [DATA_ENRICHMENT, KNOWLEDGE_RETRIEVAL]


def seed_bcc_cognitive(db: Session, tenant_id: str) -> None:
    """Seed the cognitive structure — idempotent."""
    existing = db.query(BccDomain).filter_by(tenant_id=tenant_id).count()
    if existing > 0:
        logger.info("bcc_cognitive_already_seeded", domain_count=existing)
        return

    total_domains = 0
    total_intents = 0
    total_tasks = 0

    all_structures = COGNITIVE_STRUCTURE + PIPELINE_VISIBILITY_STRUCTURE

    for domain_def in all_structures:
        domain = BccDomain(
            id=generate_uuid(),
            tenant_id=tenant_id,
            name=domain_def["name"],
            description=domain_def["description"],
            icon=domain_def["icon"],
        )
        db.add(domain)
        db.flush()
        total_domains += 1

        for intent_def in domain_def["intents"]:
            intent = BccIntent(
                id=generate_uuid(),
                tenant_id=tenant_id,
                name=intent_def["name"],
                description=intent_def["description"],
                category=intent_def.get("category"),
                trigger_phrases=intent_def["trigger_phrases"],
                domain_id=domain.id,
                workflow_key=intent_def["workflow_key"],
                pipeline_key=intent_def.get("pipeline_key"),
            )
            db.add(intent)
            db.flush()
            total_intents += 1

            for idx, task_def in enumerate(intent_def["tasks"]):
                task_tpl = BccTaskTemplate(
                    id=generate_uuid(),
                    tenant_id=tenant_id,
                    name=task_def["name"],
                    description=task_def.get("description", task_def["name"]),
                    context=task_def.get("context", {}),
                    frequency="ad_hoc",
                    category=intent_def.get("category"),
                )
                db.add(task_tpl)
                db.flush()

                link = BccIntentTask(
                    id=generate_uuid(),
                    tenant_id=tenant_id,
                    intent_id=intent.id,
                    task_template_id=task_tpl.id,
                    sort_order=idx,
                    tool_name=task_def.get("tool_name"),
                )
                db.add(link)
                total_tasks += 1

    db.commit()
    logger.info(
        "bcc_cognitive_seeded",
        domains=total_domains,
        intents=total_intents,
        tasks=total_tasks,
    )
