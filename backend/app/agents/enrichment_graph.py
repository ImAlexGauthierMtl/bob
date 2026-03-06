"""LangGraph enrichment pipeline — orchestrates the full enrichment flow.

UNRULED PATTERN — No HDQ template for LangGraph graph definitions.

Pipeline: search → scrape → extract
"""

from langgraph.graph import StateGraph, END
import structlog

from app.agents.state import EnrichmentState
from app.agents.nodes.search_node import search_node
from app.agents.nodes.scraper_node import scraper_node
from app.agents.nodes.extraction_node import extraction_node

logger = structlog.get_logger(__name__)


def should_continue(state: EnrichmentState) -> str:
    """Decide whether to continue or stop based on state."""
    if state.get("error"):
        return "end"
    return "continue"


def build_enrichment_graph() -> StateGraph:
    """Build and compile the enrichment pipeline graph.

    Flow:
        search → scrape → extract → END
    """
    graph = StateGraph(EnrichmentState)

    # Add nodes
    graph.add_node("search", search_node)
    graph.add_node("scrape", scraper_node)
    graph.add_node("extract", extraction_node)

    # Define edges
    graph.set_entry_point("search")
    graph.add_edge("search", "scrape")
    graph.add_edge("scrape", "extract")
    graph.add_edge("extract", END)

    return graph.compile()


# Compiled graph — ready to invoke
enrichment_pipeline = build_enrichment_graph()


async def run_enrichment(
    organization_id: str,
    organization_name: str,
    tenant_id: str,
    user_email: str,
) -> dict:
    """Run the enrichment pipeline for an organization.

    Args:
        organization_id: UUID of the organization to enrich
        organization_name: Name to search for
        tenant_id: Tenant ID for persistence
        user_email: Email of the user who triggered enrichment

    Returns:
        dict with extracted organization fields
    """
    initial_state: EnrichmentState = {
        "organization_id": organization_id,
        "organization_name": organization_name,
        "tenant_id": tenant_id,
        "user_email": user_email,
        "search_results": [],
        "urls_to_scrape": [],
        "scraped_data": [],
        "extracted": {},
        "status": "searching",
        "error": None,
    }

    logger.info(
        "enrichment_pipeline_start",
        organization=organization_name,
        org_id=organization_id,
    )

    result = await enrichment_pipeline.ainvoke(initial_state)

    logger.info(
        "enrichment_pipeline_complete",
        organization=organization_name,
        status=result.get("status"),
        fields_extracted=len(result.get("extracted", {})),
    )

    return result
