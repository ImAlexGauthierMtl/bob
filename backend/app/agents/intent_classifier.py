"""Intent Classifier for Bob — Layer 1 of the Intent Router.

Single LLM call with a single 'classify' tool to detect user intent
and extract structured entities. Replaces the unreliable 18-tool
tool-calling pattern for CRM actions.
"""

import json
import structlog
from dataclasses import dataclass, field
from typing import Optional

from groq import Groq
from app.config import settings

logger = structlog.get_logger(__name__)


def load_supported_intents_from_bcc(db, tenant_id: str) -> list[str]:
    """Load intent names from BCC, falling back to hardcoded list."""
    try:
        from app.domain.entities.bcc_entities import BccIntent
        names = [
            r[0] for r in
            db.query(BccIntent.name).filter_by(tenant_id=tenant_id).all()
        ]
        if names:
            if "general_chat" not in names:
                names.append("general_chat")
            logger.info("intents_loaded_from_bcc", count=len(names))
            return names
    except Exception as e:
        logger.warning("bcc_intent_load_failed", error=str(e))
    return SUPPORTED_INTENTS


# ── Supported intents (hardcoded fallback) ────────────────────
SUPPORTED_INTENTS = [
    "create_prospect",      # new prospect/opportunity with org + contact + product
    "search_entity",        # find/search an org, contact, or opportunity
    "navigate",             # go to a page in the CRM
    "get_pipeline",         # pipeline stats / sales overview
    "create_contact",       # add a contact (standalone, no opportunity)
    "top_opportunities",    # best deals by amount
    "closing_this_month",   # opps to close this month
    "stale_deals",          # deals inactive 30+ days
    "pipeline_value",       # pipeline value breakdown
    "dormant_contacts",     # contacts not contacted in 5+ months
    "recent_contacts",      # recently added contacts
    "contacts_no_email",    # contacts missing email
    "accounts_no_opp",      # accounts without opportunities
    "most_active_accounts", # top accounts by opp count
    "accounts_by_industry", # accounts grouped by industry
    "list_products",        # show product catalog
    "daily_summary",        # daily overview stats
    "create_activity",      # log a call, email, meeting, task, note
    "today_activities",     # activities due today
    "overdue_activities",   # overdue/past due activities
    "build_bcc",            # configure Bob, set up BCC, deep agent invocation
    "general_chat",         # everything else — free conversation
]


# ── Classify tool schema (the ONLY tool the classifier LLM uses) ──
CLASSIFY_TOOL = {
    "type": "function",
    "function": {
        "name": "classify",
        "description": (
            "Classify the user's intent and extract structured entities from their message. "
            "Always call this tool. Extract as many entities as you can find in the message."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": SUPPORTED_INTENTS,
                    "description": (
                        "The user's primary intent. Use 'create_prospect' for any request to "
                        "create an opportunity, prospect, deal, or add a new client account with "
                        "an opportunity. Use 'search_entity' for finding/searching existing records. "
                        "Use 'navigate' to go to a CRM page. Use 'general_chat' for questions, "
                        "greetings, or anything that doesn't map to CRM actions."
                    ),
                },
                "entities": {
                    "type": "object",
                    "description": "Structured data extracted from the user's message.",
                    "properties": {
                        "org_name": {
                            "type": "string",
                            "description": "Organization/company/business name",
                        },
                        "contact_first": {
                            "type": "string",
                            "description": "Contact first name",
                        },
                        "contact_last": {
                            "type": "string",
                            "description": "Contact last name",
                        },
                        "email": {
                            "type": "string",
                            "description": "Contact email address",
                        },
                        "phone": {
                            "type": "string",
                            "description": "Contact phone number",
                        },
                        "product_name": {
                            "type": "string",
                            "description": "Product or service name mentioned",
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Number of units/licenses/seats",
                        },
                        "amount": {
                            "type": "number",
                            "description": "Monetary value/deal amount",
                        },
                        "page": {
                            "type": "string",
                            "description": "CRM page to navigate to (dashboard, organizations, contacts, opportunities, etc.)",
                        },
                        "search_query": {
                            "type": "string",
                            "description": "Search query text when intent is search_entity",
                        },
                        "entity_type": {
                            "type": "string",
                            "enum": ["organization", "contact", "opportunity"],
                            "description": "Type of entity being searched for",
                        },
                    },
                },
            },
            "required": ["intent", "entities"],
        },
    },
}


# ── Classifier system prompt (minimal, focused) ──────────────
CLASSIFIER_PROMPT = """You are a CRM intent classifier. Your ONLY job is to:
1. Identify what the user wants to do (intent)
2. Extract structured data from their message (entities)

You MUST call the 'classify' tool with your analysis. Do NOT respond with text.
IMPORTANT: Only include entity fields that have real values. Do NOT include fields with null values. Omit any field you don't have data for.

Intent guidelines:
- "create_prospect" = user wants to add a new business opportunity, prospect, deal, or client
- "search_entity" = user wants to find, search, or look up an existing record
- "navigate" = user wants to go to a specific page in the CRM
- "get_pipeline" = user asks about pipeline, sales stats, deal overview
- "create_contact" = user wants to add a contact WITHOUT creating an opportunity
- "top_opportunities" = user asks for their best deals, top opportunities, biggest deals
- "closing_this_month" = user asks what's closing this month, upcoming closes
- "stale_deals" = user asks about stuck deals, stagnant opportunities, inactive deals
- "pipeline_value" = user asks about pipeline value, deal amounts, revenue breakdown
- "dormant_contacts" = user asks who they haven't called, dormant contacts, inactive contacts
- "recent_contacts" = user asks about recently added contacts, new contacts
- "contacts_no_email" = user asks about contacts missing emails, incomplete data
- "accounts_no_opp" = user asks about accounts without deals, untapped potential
- "most_active_accounts" = user asks about their most active accounts, best clients
- "accounts_by_industry" = user asks for industry breakdown, accounts by sector
- "list_products" = user asks to see products, catalog, available services
- "daily_summary" = user asks for a summary, morning briefing, standup prep, "comment va mon pipeline"
- "create_activity" = user wants to log a call, note an email, schedule a meeting, create a task or note
- "today_activities" = user asks about today's activities, schedule, what's planned
- "overdue_activities" = user asks about overdue activities, missed tasks, late reminders
- "build_bcc" = user wants to configure Bob, set up domains/intents/tasks in the BCC, "make this happen to the BCC"
- "general_chat" = greetings, questions, help, anything else

For contact names, split into first and last name when possible.
For organizations, extract the business/company name exactly as stated.

/no_think"""


@dataclass
class ExtractedEntities:
    """Structured entities extracted from the user's message."""
    org_name: Optional[str] = None
    contact_first: Optional[str] = None
    contact_last: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    amount: Optional[float] = None
    page: Optional[str] = None
    search_query: Optional[str] = None
    entity_type: Optional[str] = None


@dataclass
class ClassifiedIntent:
    """Result of intent classification."""
    intent: str
    entities: ExtractedEntities
    confidence: float = 1.0
    raw_response: Optional[dict] = field(default=None, repr=False)


def _parse_entities(raw: dict) -> ExtractedEntities:
    """Parse entities dict into ExtractedEntities, stripping None/null values."""
    return ExtractedEntities(
        org_name=raw.get("org_name") or None,
        contact_first=raw.get("contact_first") or None,
        contact_last=raw.get("contact_last") or None,
        email=raw.get("email") or None,
        phone=raw.get("phone") or None,
        product_name=raw.get("product_name") or None,
        quantity=raw.get("quantity") if raw.get("quantity") else None,
        amount=raw.get("amount") if raw.get("amount") else None,
        page=raw.get("page") or None,
        search_query=raw.get("search_query") or None,
        entity_type=raw.get("entity_type") or None,
    )


def _try_parse_failed_generation(error_str: str) -> Optional[ClassifiedIntent]:
    """Extract classification from Groq's tool_use_failed error response.

    When the LLM outputs null for typed fields, Groq rejects the tool call
    but includes the full LLM output in 'failed_generation'. We parse it,
    strip nulls, and use the result.
    """
    import re
    # Extract the failed_generation JSON from the error string
    fg_match = re.search(r"failed_generation.*?\{\"name\".*?\"classify\".*?\"arguments\":\s*(\{.*\})\}", error_str, re.DOTALL)
    if not fg_match:
        return None

    try:
        raw_args = json.loads(fg_match.group(1))
        intent = raw_args.get("intent", "general_chat")
        if intent not in SUPPORTED_INTENTS:
            intent = "general_chat"

        raw_entities = raw_args.get("entities", {})
        # Strip null values
        clean_entities = {k: v for k, v in raw_entities.items() if v is not None}
        entities = _parse_entities(clean_entities)

        logger.info(
            "intent_classified_from_failed_gen",
            intent=intent,
            entities={k: v for k, v in clean_entities.items() if v},
        )

        return ClassifiedIntent(
            intent=intent,
            entities=entities,
            raw_response=raw_args,
        )
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("failed_gen_parse_error", error=str(e))
        return None


def _build_classify_tool(intent_list: list[str]) -> dict:
    """Build CLASSIFY_TOOL dynamically from an intent list."""
    tool = json.loads(json.dumps(CLASSIFY_TOOL))
    tool["function"]["parameters"]["properties"]["intent"]["enum"] = intent_list
    return tool


def classify_message(
    message: str,
    conversation_context: list[dict] | None = None,
    db=None,
    tenant_id: str | None = None,
) -> ClassifiedIntent:
    """Classify a user message into an intent with extracted entities.

    Uses a single LLM call with a single 'classify' tool.
    Falls back to 'general_chat' if classification fails.
    When db and tenant_id are provided, loads intents from BCC.

    Args:
        message: The user's message text.
        conversation_context: Optional recent messages for context.
        db: Optional SQLAlchemy session to load BCC intents.
        tenant_id: Optional tenant ID for BCC filtering.

    Returns:
        ClassifiedIntent with intent name and extracted entities.
    """
    active_intents = SUPPORTED_INTENTS
    if db and tenant_id:
        active_intents = load_supported_intents_from_bcc(db, tenant_id)

    classify_tool = _build_classify_tool(active_intents)
    messages = [{"role": "system", "content": CLASSIFIER_PROMPT}]

    # Add limited conversation context if available (last 4 messages max)
    if conversation_context:
        for msg in conversation_context[-4:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": message})

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.bob_model,
            messages=messages,
            tools=[classify_tool],
            tool_choice={"type": "function", "function": {"name": "classify"}},
            temperature=0.1,
            max_tokens=512,
        )

        choice = response.choices[0]

        if choice.message.tool_calls:
            tc = choice.message.tool_calls[0]
            args = json.loads(tc.function.arguments)

            intent = args.get("intent", "general_chat")
            if intent not in active_intents:
                intent = "general_chat"

            raw_entities = args.get("entities", {})
            entities = _parse_entities(raw_entities)

            logger.info(
                "intent_classified",
                intent=intent,
                entities={k: v for k, v in raw_entities.items() if v},
                tokens_in=response.usage.prompt_tokens if response.usage else 0,
                tokens_out=response.usage.completion_tokens if response.usage else 0,
            )

            return ClassifiedIntent(
                intent=intent,
                entities=entities,
                raw_response=args,
            )

        # No tool call — fallback
        logger.warning("classifier_no_tool_call", content=choice.message.content[:200] if choice.message.content else "")
        return ClassifiedIntent(intent="general_chat", entities=ExtractedEntities())

    except Exception as e:
        error_str = str(e)
        # Try to salvage classification from Groq's failed_generation
        if "tool_use_failed" in error_str or "failed_generation" in error_str:
            result = _try_parse_failed_generation(error_str)
            if result:
                return result
        logger.error("classifier_error", error=error_str)
        return ClassifiedIntent(intent="general_chat", entities=ExtractedEntities())

