"""Scraper node — fetches web pages and extracts text content.

UNRULED PATTERN — No HDQ template for web scraping.
"""

import httpx
import re
import structlog

from app.agents.state import EnrichmentState

logger = structlog.get_logger(__name__)


def clean_html(html: str) -> str:
    """Strip HTML tags and extract readable text."""
    # Remove script and style elements
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Truncate to avoid token limits
    return text[:8000]


async def scraper_node(state: EnrichmentState) -> dict:
    """Scrape URLs and extract text content.

    Returns updated state with scraped_data.
    """
    urls = state.get("urls_to_scrape", [])
    logger.info("scrape_start", url_count=len(urls))

    scraped = []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CrooBot/1.0; +https://croo.digital)"
    }

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for url in urls:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "text/html" in content_type:
                        text = clean_html(response.text)
                        if len(text) > 100:
                            scraped.append({"url": url, "content": text})
                            logger.info("scrape_ok", url=url, chars=len(text))
                        else:
                            logger.info("scrape_skip_short", url=url)
                    else:
                        logger.info("scrape_skip_content_type", url=url, content_type=content_type)
                else:
                    logger.info("scrape_skip_status", url=url, status=response.status_code)
            except Exception as e:
                logger.error("scrape_error", url=url, error=str(e))

    logger.info("scrape_complete", pages_scraped=len(scraped))

    return {
        "scraped_data": scraped,
        "status": "extracting",
    }
