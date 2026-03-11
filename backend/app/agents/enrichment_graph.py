"""LangGraph enrichment pipeline — Hunter.io + scrape + Groq extraction + Compound.

Maps search already provides name, address, phone, website, industry.
This pipeline adds:
1. Hunter.io Domain Search + Company Enrichment (contacts, industry, social)
2. Website scraping (deep pages: about, contact, team, services)
3. Groq LLM extraction (structured data from all sources)
4. Groq Compound deep intelligence (news, clients, competitors, etc.)

Flow: hunter → scrape → extract → compound → END
"""

from langgraph.graph import StateGraph, END
import structlog

from app.agents.state import EnrichmentState
from app.agents.nodes.hunter_node import hunter_node
from app.agents.nodes.scraper_node import scraper_node
from app.agents.nodes.extraction_node import extraction_node
from app.agents.nodes.compound_node import compound_node

logger = structlog.get_logger(__name__)


def build_enrichment_graph() -> StateGraph:
    """Build and compile the enrichment pipeline.

    Flow: hunter → scrape → extract → compound → END
    Each node gracefully skips if its prerequisites aren't met.
    """
    graph = StateGraph(EnrichmentState)

    graph.add_node("hunter", hunter_node)
    graph.add_node("scrape", scraper_node)
    graph.add_node("extract", extraction_node)
    graph.add_node("compound", compound_node)

    graph.set_entry_point("hunter")
    graph.add_edge("hunter", "scrape")
    graph.add_edge("scrape", "extract")
    graph.add_edge("extract", "compound")
    graph.add_edge("compound", END)

    return graph.compile()


enrichment_pipeline = build_enrichment_graph()


async def run_enrichment(
    organization_id: str,
    organization_name: str,
    tenant_id: str,
    user_email: str,
    website_url: str | None = None,
) -> dict:
    """Run the enrichment pipeline for an organization.

    Uses the website URL from Maps data to:
    1. Query Hunter.io for contacts and company data
    2. Scrape the website for deep content
    3. Extract structured data with Groq LLM
    4. Deep intelligence with Groq Compound
    """
    # Build URLs to scrape from the website
    urls_to_scrape = []
    if website_url:
        urls_to_scrape.append(website_url)

    initial_state: EnrichmentState = {
        "organization_id": organization_id,
        "organization_name": organization_name,
        "tenant_id": tenant_id,
        "user_email": user_email,
        "hunter_contacts": [],
        "hunter_company": {},
        "search_results": [],
        "urls_to_scrape": urls_to_scrape,
        "scraped_data": [],
        "regex_data": {},
        "extracted": {},
        "organization_profile": {},
        "intelligence_sections": [],
        "status": "hunter",
        "error": None,
    }

    logger.info(
        "enrichment_pipeline_start",
        organization=organization_name,
        org_id=organization_id,
        website=website_url,
    )

    result = await enrichment_pipeline.ainvoke(initial_state)

    logger.info(
        "enrichment_pipeline_complete",
        organization=organization_name,
        status=result.get("status"),
        fields_extracted=len(result.get("extracted", {})),
        hunter_contacts=len(result.get("hunter_contacts", [])),
        intelligence_sections=len(result.get("intelligence_sections", [])),
    )

    return result
