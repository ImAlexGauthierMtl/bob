"""Agent state schema for LangGraph enrichment pipeline.

UNRULED PATTERN — No HDQ template for LangGraph state definitions.
"""

from typing import TypedDict, Optional, List


class SearchResult(TypedDict):
    """A single search result from Serper."""

    title: str
    link: str
    snippet: str


class ScrapedData(TypedDict):
    """Data extracted from a scraped page."""

    url: str
    content: str


class EnrichmentState(TypedDict):
    """State that flows through the LangGraph enrichment pipeline.

    Each node reads and writes to this shared state.
    """

    # Input
    organization_id: str
    organization_name: str
    tenant_id: str
    user_email: str

    # Search phase
    search_results: List[SearchResult]
    urls_to_scrape: List[str]

    # Scrape phase
    scraped_data: List[ScrapedData]

    # Extraction phase
    extracted: dict  # Organization fields extracted by LLM

    # Status
    status: str  # "pending" | "searching" | "scraping" | "extracting" | "done" | "error"
    error: Optional[str]
