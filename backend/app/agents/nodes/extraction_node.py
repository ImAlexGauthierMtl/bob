"""Extraction node — uses Groq LLM to extract structured organization data.

UNRULED PATTERN — No HDQ template for LLM-based structured extraction.
"""

import json
import structlog

from app.agents.llm_client import llm_client
from app.agents.state import EnrichmentState

logger = structlog.get_logger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are a data extraction specialist. Given web content about a company, extract structured information.

Return a JSON object with ONLY these fields (use null for unknown):
{
    "industry": "string — primary industry (e.g., Aerospace, Technology, Healthcare)",
    "website": "string — official website URL",
    "phone": "string — main phone number",
    "email": "string — main contact email",
    "address_street": "string",
    "address_city": "string",
    "address_state": "string — state/province",
    "address_country": "string",
    "address_postal_code": "string",
    "employee_count": "integer — approximate number of employees",
    "annual_revenue": "float — annual revenue in USD",
    "description": "string — one paragraph company description",
    "linkedin_url": "string — LinkedIn company page URL",
    "org_type": "string — one of: CORPORATION, SMB, STARTUP, GOVERNMENT, NONPROFIT, OTHER"
}

RULES:
- Only include information you are confident about
- Use null for anything uncertain
- Revenue should be in USD (convert if needed)
- Employee count should be a number, not a range
- Description should be factual, 2-3 sentences max
"""


async def extraction_node(state: EnrichmentState) -> dict:
    """Extract structured organization data from scraped content using Groq LLM.

    Returns updated state with extracted fields.
    """
    name = state["organization_name"]
    scraped = state.get("scraped_data", [])
    search_results = state.get("search_results", [])

    logger.info("extraction_start", organization=name, sources=len(scraped))

    # Build context from all sources
    context_parts = [f"Company name: {name}\n"]

    # Add search snippets
    for sr in search_results[:5]:
        context_parts.append(f"Search result: {sr['title']} — {sr['snippet']}")

    # Add scraped content
    for sd in scraped[:3]:  # Limit to 3 pages to stay within context
        context_parts.append(f"\n--- Content from {sd['url']} ---\n{sd['content'][:3000]}")

    context = "\n".join(context_parts)

    prompt = f"""Extract structured company information for "{name}" from the following web content:

{context}

Return the JSON object with extracted fields."""

    try:
        response = llm_client.chat(
            prompt=prompt,
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            json_mode=True,
            temperature=0.0,
            max_tokens=2048,
        )

        extracted = json.loads(response)

        # Clean nulls
        extracted = {k: v for k, v in extracted.items() if v is not None}

        logger.info("extraction_complete", organization=name, fields_found=len(extracted))

        return {
            "extracted": extracted,
            "status": "done",
        }

    except json.JSONDecodeError as e:
        logger.error("extraction_json_error", organization=name, error=str(e))
        return {"extracted": {}, "status": "error", "error": f"JSON parse error: {e}"}
    except Exception as e:
        logger.error("extraction_error", organization=name, error=str(e))
        return {"extracted": {}, "status": "error", "error": str(e)}
