"""Extraction node — uses Groq LLM to extract structured organization data.

Deep extraction: company info, contacts, services/products, social media,
key people, and business details.
"""

import json
import structlog

from app.agents.llm_client import llm_client
from app.agents.state import EnrichmentState

logger = structlog.get_logger(__name__)

# ── Flat extraction prompt (backward compat) ─────────────────
FLAT_SYSTEM_PROMPT = """You are a data extraction specialist. Given web content about a company, extract structured information.

Return a JSON object with ONLY these fields (use null for unknown):
{
    "industry": "string — primary industry",
    "website": "string — official website URL",
    "phone": "string — main phone number",
    "email": "string — main contact email",
    "address_street": "string",
    "address_city": "string",
    "address_state": "string — state/province",
    "address_country": "string",
    "address_postal_code": "string",
    "employee_count": "integer",
    "annual_revenue": "float — in USD",
    "description": "string — 2-3 sentence company description",
    "linkedin_url": "string — LinkedIn company page URL",
    "org_type": "string — CORPORATION | SMB | STARTUP | GOVERNMENT | NONPROFIT | OTHER"
}

RULES:
- Only include information you are confident about
- Use null for anything uncertain
- Description should be factual, 2-3 sentences max
"""

# ── Deep profile extraction prompt ───────────────────────────
DEEP_SYSTEM_PROMPT = """You are an advanced business intelligence extraction specialist. Given web content about a company, extract COMPREHENSIVE structured information.

Return a JSON object with these fields (use null for unknown):
{
    "company_info": {
        "name": "official company name",
        "legal_name": "legal or registered name if different",
        "industry": "primary industry",
        "sub_industry": "specific niche",
        "description": "detailed 3-5 sentence company description",
        "founding_year": "integer",
        "org_type": "CORPORATION | SMB | STARTUP | GOVERNMENT | NONPROFIT | OTHER",
        "employee_count": "integer",
        "annual_revenue": "float in USD",
        "languages": ["languages used"]
    },
    "contact_info": {
        "main_phone": "string",
        "other_phones": ["string"],
        "main_email": "string",
        "other_emails": ["string"],
        "website": "string",
        "address": {
            "street": "string",
            "city": "string",
            "state": "string",
            "country": "string",
            "postal_code": "string"
        }
    },
    "social_media": {
        "linkedin_url": "string",
        "facebook_url": "string",
        "instagram_url": "string",
        "twitter_url": "string",
        "youtube_url": "string",
        "tiktok_url": "string"
    },
    "key_people": [
        {
            "name": "string",
            "title": "role/position",
            "email": "string or null",
            "phone": "string or null",
            "linkedin": "string or null"
        }
    ],
    "services_products": [
        {
            "name": "service or product name",
            "description": "brief description",
            "category": "category"
        }
    ],
    "business_details": {
        "target_market": "who they serve",
        "geographic_coverage": "where they operate",
        "certifications": ["certifications, awards"],
        "partners": ["notable partners"],
        "unique_selling_points": ["what differentiates them"]
    }
}

RULES:
- Extract EVERYTHING you can find, be thorough
- For key_people, include anyone mentioned by name WITH a role
- For services/products, list ALL distinct offerings
- Be precise with contact information
- Use null only for truly unknown fields
"""


async def extraction_node(state: EnrichmentState) -> dict:
    """Extract structured organization data from scraped content using Groq LLM.

    Runs two extractions:
    1. Flat fields (backward compat: industry, phone, etc.)
    2. Deep profile (services, contacts, social, key people, etc.)

    Returns updated state with extracted fields and organization_profile.
    """
    name = state["organization_name"]
    scraped = state.get("scraped_data", [])
    search_results = state.get("search_results", [])
    regex_data = state.get("regex_data", {})

    logger.info("extraction_start", organization=name, sources=len(scraped))

    # Build context from all sources
    context_parts = [f"Company name: {name}\n"]

    for sr in search_results[:5]:
        context_parts.append(f"Search result: {sr['title']} — {sr['snippet']}")

    for sd in scraped[:5]:
        context_parts.append(f"\n--- Content from {sd['url']} ---\n{sd['content'][:3000]}")

    context = "\n".join(context_parts)

    # Add regex data to context
    regex_context = ""
    if regex_data:
        parts = []
        for key, vals in regex_data.items():
            if vals:
                parts.append(f"- {key}: {vals}")
        if parts:
            regex_context = "\n\nAutomated extraction found:\n" + "\n".join(parts)

    # ── Extraction 1: Flat fields (backward compat) ──
    flat_prompt = f"""Extract structured company information for "{name}" from the following web content:

{context[:5000]}

Return the JSON object with extracted fields."""

    extracted = {}
    try:
        flat_response = llm_client.chat(
            prompt=flat_prompt,
            system_prompt=FLAT_SYSTEM_PROMPT,
            json_mode=True,
            temperature=0.0,
            max_tokens=2048,
        )
        extracted = json.loads(flat_response)
        extracted = {k: v for k, v in extracted.items() if v is not None}
        logger.info("flat_extraction_complete", organization=name, fields_found=len(extracted))
    except Exception as e:
        logger.error("flat_extraction_error", organization=name, error=str(e))

    # ── Extraction 2: Deep profile ──
    deep_prompt = f"""Extract comprehensive business intelligence for "{name}" from the following sources:

{context[:8000]}{regex_context}

Return the comprehensive JSON object."""

    organization_profile = {}
    try:
        deep_response = llm_client.chat(
            prompt=deep_prompt,
            system_prompt=DEEP_SYSTEM_PROMPT,
            json_mode=True,
            temperature=0.0,
            max_tokens=4096,
        )
        organization_profile = json.loads(deep_response)
        logger.info("deep_extraction_complete", organization=name, categories=list(organization_profile.keys()))
    except Exception as e:
        logger.error("deep_extraction_error", organization=name, error=str(e))

    return {
        "extracted": extracted,
        "organization_profile": organization_profile,
        "status": "done",
    }
