"""Entity Extractor — LLM-in-the-Loop extraction from chat history.

Uses a single Groq LLM call per workflow turn to:
1. Read the full chat history (last 10 messages)
2. Read the BCC-defined required/optional fields
3. Extract all entities the user already mentioned
4. Return collected{} vs missing[] so the workflow asks only what's needed.
"""

import json
import structlog
from typing import Optional

from groq import Groq
from app.config import settings

logger = structlog.get_logger(__name__)


# ── Default field descriptions (used when BCC doesn't provide them) ──

DEFAULT_FIELD_DESCRIPTIONS: dict[str, str] = {
    # Organization
    "org_name": "Organization/company/business name",
    "org_address": "Physical street address",
    "org_phone": "Organization phone number",
    "org_website": "Website URL (e.g. https://...)",
    "org_industry": "Industry or business sector",
    # Contact
    "contact_first": "Contact first name",
    "contact_last": "Contact last name",
    "contact_email": "Contact email address",
    "contact_phone": "Contact direct phone number",
    # Opportunity
    "opp_name": "Opportunity/deal name",
    "amount": "Deal monetary value",
    "product_name": "Product or service name",
    # Activity
    "activity_type": "Activity type (CALL, EMAIL, MEETING, TASK, NOTE)",
    "activity_subject": "Subject or title of the activity",
    "activity_notes": "Notes or description",
    # Search
    "search_query": "Search query text",
    "entity_type": "Entity type (organization, contact, opportunity)",
    # Navigation
    "page": "CRM page name to navigate to",
    # KB
    "kb_topic": "Knowledge Base article topic",
}


# ── Field type mapping for the extraction tool schema ──

FIELD_TYPES: dict[str, str] = {
    "amount": "number",
    "quantity": "integer",
}


# ── System prompt for the extractor ──

EXTRACTOR_PROMPT = """You are an entity extractor for a CRM assistant called Bob.
Your job is to analyze the ENTIRE conversation history and extract ALL structured 
information the user has provided across ALL their messages.

Rules:
- Extract ONLY values the user explicitly stated or clearly implied
- Do NOT guess or infer values that weren't mentioned
- If the user gave a full name, split it into first + last
- If the user gave an email, extract it precisely
- If the user mentioned a company name, extract it as org_name
- Look at ALL messages in the conversation, not just the last one
- The user may provide info across multiple messages — collect everything

Call the extract_entities tool with every confirmed value. Omit any field you
don't have data for — do not include null or empty string values.

/no_think"""


def build_extract_tool(fields: dict[str, str]) -> dict:
    """Build the OpenAI-format extract_entities tool from a field map.

    Args:
        fields: {field_name: description} for all fields to extract.

    Returns:
        Tool definition dict for the Groq API.
    """
    properties = {}
    for name, desc in fields.items():
        field_type = FIELD_TYPES.get(name, "string")
        properties[name] = {"type": field_type, "description": desc}

    return {
        "type": "function",
        "function": {
            "name": "extract_entities",
            "description": (
                "Extract all structured information from the conversation. "
                "Only include fields with real values — omit anything unknown."
            ),
            "parameters": {
                "type": "object",
                "properties": properties,
            },
        },
    }


def _build_field_map_from_bcc(
    db,
    tenant_id: str,
    intent_name: str,
) -> dict[str, str]:
    """Load required + optional fields from BCC task steps for an intent.

    Merges all `required_info` and `optional_info` from every task step
    in the intent's task chain, then maps each to a human description.

    Falls back to DEFAULT_FIELD_DESCRIPTIONS for any field without
    a BCC-provided description.

    Args:
        db: SQLAlchemy session.
        tenant_id: Tenant UUID.
        intent_name: e.g. "create_prospect".

    Returns:
        {field_name: description} dict.
    """
    try:
        from app.domain.entities.bcc_entities import (
            BccIntent,
            BccIntentTask,
            BccTaskTemplate,
        )

        intent = (
            db.query(BccIntent)
            .filter_by(tenant_id=tenant_id, name=intent_name)
            .first()
        )
        if not intent:
            logger.debug("extractor_no_bcc_intent", intent=intent_name)
            return {}

        fields: dict[str, str] = {}
        for link in intent.task_links:
            ctx = link.task_template.context or {}
            for f in ctx.get("required_info", []):
                if f not in fields:
                    desc = ctx.get("field_descriptions", {}).get(f)
                    fields[f] = desc or DEFAULT_FIELD_DESCRIPTIONS.get(f, f)
            for f in ctx.get("optional_info", []):
                if f not in fields:
                    desc = ctx.get("field_descriptions", {}).get(f)
                    fields[f] = desc or DEFAULT_FIELD_DESCRIPTIONS.get(f, f)

        logger.debug(
            "extractor_bcc_fields_loaded",
            intent=intent_name,
            field_count=len(fields),
        )
        return fields

    except Exception as e:
        logger.warning("extractor_bcc_load_failed", error=str(e))
        return {}


# ── Default field sets per intent (fallback when BCC is empty) ──

_FALLBACK_FIELDS: dict[str, list[str]] = {
    "create_prospect": [
        "org_name",
        "contact_first",
        "contact_last",
        "contact_email",
        "contact_phone",
        "opp_name",
        "amount",
        "product_name",
    ],
    "create_contact": [
        "org_name",
        "contact_first",
        "contact_last",
        "contact_email",
        "contact_phone",
    ],
    "create_activity": [
        "activity_type",
        "activity_subject",
        "activity_notes",
        "org_name",
        "contact_first",
        "contact_last",
    ],
}


def get_extraction_fields(
    intent_name: str,
    db=None,
    tenant_id: str | None = None,
) -> dict[str, str]:
    """Get the field map for extraction, from BCC or fallback.

    Args:
        intent_name: The classified intent name.
        db: Optional SQLAlchemy session.
        tenant_id: Optional tenant UUID.

    Returns:
        {field_name: description} dict of all fields to extract.
    """
    # Try BCC first
    if db and tenant_id:
        bcc_fields = _build_field_map_from_bcc(db, tenant_id, intent_name)
        if bcc_fields:
            return bcc_fields

    # Fallback
    fallback = _FALLBACK_FIELDS.get(intent_name, [])
    return {f: DEFAULT_FIELD_DESCRIPTIONS.get(f, f) for f in fallback}


def extract_entities(
    chat_history: list[dict],
    fields: dict[str, str],
) -> dict[str, str | int | float]:
    """Run LLM extraction on the chat history.

    Args:
        chat_history: List of {"role": "user"|"assistant", "content": "..."}.
        fields: {field_name: description} of fields to extract.

    Returns:
        Dict of extracted entities with non-null values only.
    """
    if not fields:
        return {}

    tool = build_extract_tool(fields)
    messages: list[dict] = [
        {"role": "system", "content": EXTRACTOR_PROMPT},
    ]

    # Add last 10 messages of history
    for msg in chat_history[-10:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    if len(messages) <= 1:
        # No chat history to extract from
        return {}

    try:
        client = Groq(api_key=settings.groq_api_key)
        response = client.chat.completions.create(
            model=settings.bob_model,
            messages=messages,
            tools=[tool],
            tool_choice={
                "type": "function",
                "function": {"name": "extract_entities"},
            },
            temperature=0.1,
            max_tokens=512,
        )

        choice = response.choices[0]
        if not choice.message.tool_calls:
            logger.warning("extractor_no_tool_call")
            return {}

        raw = json.loads(choice.message.tool_calls[0].function.arguments)
        # Strip null/empty values
        extracted = {k: v for k, v in raw.items() if v is not None and v != ""}

        logger.info(
            "entities_extracted",
            field_count=len(extracted),
            fields=list(extracted.keys()),
            tokens_in=response.usage.prompt_tokens if response.usage else 0,
            tokens_out=response.usage.completion_tokens if response.usage else 0,
        )
        return extracted

    except Exception as e:
        error_str = str(e)
        # Try to salvage from Groq's failed_generation
        if "failed_generation" in error_str:
            try:
                import re
                fg_match = re.search(
                    r'"arguments":\s*(\{.*\})',
                    error_str,
                    re.DOTALL,
                )
                if fg_match:
                    raw = json.loads(fg_match.group(1))
                    extracted = {
                        k: v
                        for k, v in raw.items()
                        if v is not None and v != ""
                    }
                    logger.info(
                        "entities_extracted_from_failed_gen",
                        field_count=len(extracted),
                    )
                    return extracted
            except Exception:
                pass

        logger.error("extractor_error", error=error_str)
        return {}


def run_extraction(
    chat_history: list[dict],
    required_fields: dict[str, str],
    optional_fields: dict[str, str] | None = None,
    already_collected: dict | None = None,
) -> tuple[dict, list[str]]:
    """Extract entities and determine what's missing.

    This is the main entry point used by WorkflowEngine.

    Args:
        chat_history: Full chat session messages.
        required_fields: {field_name: description} that MUST be collected.
        optional_fields: {field_name: description} that are nice-to-have.
        already_collected: Entities already in workflow state (won't re-extract).

    Returns:
        (collected, missing) where:
        - collected: all extracted + already_collected entities merged
        - missing: list of required field names still not found
    """
    # Merge all fields for the extraction call
    all_fields = dict(required_fields)
    if optional_fields:
        all_fields.update(optional_fields)

    # Run extraction
    extracted = extract_entities(chat_history, all_fields)

    # Merge with already collected (state from previous turns)
    collected = dict(already_collected or {})
    for key, value in extracted.items():
        if key not in collected:  # Don't overwrite confirmed values
            collected[key] = value

    # Determine what's still missing
    missing = [
        f for f in required_fields
        if f not in collected or not collected[f]
    ]

    logger.info(
        "extraction_result",
        collected_count=len(collected),
        missing=missing,
        required_count=len(required_fields),
    )

    return collected, missing
