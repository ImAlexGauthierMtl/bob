"""LangGraph enrichment pipeline — scrape website + Groq extraction.

Maps search already provides name, address, phone, website, industry.
This pipeline adds: description, employee count, revenue, LinkedIn, etc.
by scraping the org's website and extracting with Groq.

NO additional Serper queries — Maps is the only Serper call.
"""

from langgraph.graph import StateGraph, END
import structlog

from app.agents.state import EnrichmentState
from app.agents.nodes.scraper_node import scraper_node
from app.agents.nodes.extraction_node import extraction_node

logger = structlog.get_logger(__name__)


def build_enrichment_graph() -> StateGraph:
    """Build and compile the enrichment pipeline.

    Flow: scrape → extract → END
    (search step removed — Maps search already done at creation)
    """
    graph = StateGraph(EnrichmentState)

    graph.add_node("scrape", scraper_node)
    graph.add_node("extract", extraction_node)

    graph.set_entry_point("scrape")
    graph.add_edge("scrape", "extract")
    graph.add_edge("extract", END)

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

    Uses the website URL from Maps data to scrape and extract info.
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
        "search_results": [],
        "urls_to_scrape": urls_to_scrape,
        "scraped_data": [],
        "regex_data": {},
        "extracted": {},
        "organization_profile": {},
        "status": "scraping",
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
    )

    return result
