"""Search node — uses Serper.dev to find company information.

Based on `http-client-service` template (RULED) adapted for Serper API.
"""

import httpx
import structlog

from app.config import settings
from app.agents.state import EnrichmentState

logger = structlog.get_logger(__name__)

SERPER_URL = "https://google.serper.dev/search"


async def search_node(state: EnrichmentState) -> dict:
    """Search for organization information using Serper.dev.

    Returns updated state with search_results and urls_to_scrape.
    """
    name = state["organization_name"]
    logger.info("search_start", organization=name)

    queries = [
        f"{name} company official website",
        f"{name} linkedin company",
        f"{name} company information employees revenue",
    ]

    all_results = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in queries:
            try:
                response = await client.post(
                    SERPER_URL,
                    json={"q": query, "num": 5},
                    headers={
                        "X-API-KEY": settings.serper_api_key,
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()

                for item in data.get("organic", [])[:3]:
                    all_results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    })

                logger.info("search_query_done", query=query, results=len(data.get("organic", [])))
            except Exception as e:
                logger.error("search_query_error", query=query, error=str(e))

    # Deduplicate URLs
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r["link"] not in seen_urls:
            seen_urls.add(r["link"])
            unique_results.append(r)

    # Take top 5 URLs to scrape
    urls = [r["link"] for r in unique_results[:5]]

    logger.info("search_complete", total_results=len(unique_results), urls_to_scrape=len(urls))

    return {
        "search_results": unique_results,
        "urls_to_scrape": urls,
        "status": "scraping",
    }
