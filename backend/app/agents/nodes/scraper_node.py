"""Scraper node — fetches web pages and extracts text content.

Deep scraping: homepage + internal pages (contact, about, services).
Also extracts emails, phones, social links via regex.
"""

import re
from urllib.parse import urljoin, urlparse

import httpx
import structlog

from app.agents.state import EnrichmentState

logger = structlog.get_logger(__name__)

# Pages most likely to contain useful business intelligence
INTERESTING_PATHS = [
    "/contact", "/contactez-nous", "/nous-joindre", "/coordonnees",
    "/a-propos", "/about", "/about-us", "/qui-sommes-nous",
    "/services", "/nos-services", "/produits", "/products",
    "/equipe", "/notre-equipe", "/team", "/our-team", "/leadership",
    "/personnel", "/staff", "/direction", "/dirigeants",
    "/carrieres", "/careers", "/partenaires", "/partners",
]

# Keywords that strongly suggest a page about team/people
TEAM_KEYWORDS = [
    "equipe", "team", "staff", "personnel", "direction",
    "dirigeant", "leadership", "founders", "fondateur",
    "management", "advisors", "conseil", "board",
]


def clean_html(html: str, max_chars: int = 6000) -> str:
    """Strip HTML tags and extract readable text."""
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def extract_regex_data(html: str) -> dict:
    """Extract emails, phones, social links from raw HTML via regex."""
    return {
        "emails": list(set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', html))),
        "phones": list(set(re.findall(r'[\+]?1?\s*[\(\-]?\d{3}[\)\-\s]*\d{3}[\-\s]?\d{4}', html))),
        "linkedin": list(set(re.findall(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w-]+/?', html))),
        "facebook": list(set(re.findall(r'https?://(?:www\.)?facebook\.com/[\w.-]+/?', html))),
        "instagram": list(set(re.findall(r'https?://(?:www\.)?instagram\.com/[\w._]+/?', html))),
        "twitter": list(set(re.findall(r'https?://(?:www\.)?(?:twitter|x)\.com/[\w._]+/?', html))),
        "youtube": list(set(re.findall(r'https?://(?:www\.)?youtube\.com/(?:channel|c|@)[\w/-]+/?', html))),
        "tiktok": list(set(re.findall(r'https?://(?:www\.)?tiktok\.com/@[\w.-]+/?', html))),
        "addresses": list(set(re.findall(
            r'\d+[,\s]+(?:rue|ch\.|chemin|boulevard|boul\.|avenue|av\.|street|road)[^<\n]{5,100}',
            html, re.IGNORECASE
        ))),
    }


def merge_regex_data(target: dict, source: dict) -> None:
    """Merge regex data from multiple pages, deduplicating."""
    for key, vals in source.items():
        if vals:
            target.setdefault(key, [])
            target[key] = list(set(target[key] + vals))


def find_internal_pages(html: str, base_url: str) -> list[str]:
    """Find internal links matching interesting patterns.

    Uses both exact path suffix matching and keyword-based matching
    for broader coverage (e.g. /notre-equipe-et-nos-valeurs).
    """
    domain = urlparse(base_url).netloc
    links = re.findall(r'href=["\']([^"\']+)["\']', html)
    found = set()
    for link in links:
        full = urljoin(base_url, link)
        parsed = urlparse(full)
        if parsed.netloc == domain:
            path = parsed.path.rstrip("/").lower()
            # Exact suffix match
            if any(path.endswith(p) for p in INTERESTING_PATHS):
                found.add(full.split("#")[0].split("?")[0])
                continue
            # Keyword-based match (catches compound URLs)
            segments = path.split("/")
            for seg in segments:
                if any(kw in seg for kw in TEAM_KEYWORDS):
                    found.add(full.split("#")[0].split("?")[0])
                    break
    return list(found)[:8]


async def scraper_node(state: EnrichmentState) -> dict:
    """Scrape homepage + internal pages and extract text + regex data.

    Returns updated state with scraped_data and regex_data.
    """
    urls = list(state.get("urls_to_scrape", []))
    logger.info("scrape_start", url_count=len(urls))

    scraped = []
    all_regex_data: dict = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8",
    }

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        # Phase 1: Scrape homepage and discover internal pages
        homepage_url = urls[0] if urls else None
        internal_pages: list[str] = []

        for url in urls:
            try:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "text/html" in content_type and len(response.text) > 100:
                        text = clean_html(response.text)
                        if len(text) > 100:
                            scraped.append({"url": url, "content": text})
                            logger.info("scrape_ok", url=url, chars=len(text))

                        # Extract regex data from raw HTML (before cleaning)
                        page_regex = extract_regex_data(response.text)
                        merge_regex_data(all_regex_data, page_regex)

                        # Find internal pages from homepage
                        if url == homepage_url:
                            internal_pages = find_internal_pages(response.text, str(response.url))
                            logger.info("internal_pages_found", count=len(internal_pages))
            except Exception as e:
                logger.error("scrape_error", url=url, error=str(e))

        # Phase 2: Scrape discovered internal pages
        for page_url in internal_pages:
            if page_url in urls:
                continue
            try:
                response = await client.get(page_url, headers=headers)
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "")
                    if "text/html" in content_type and len(response.text) > 100:
                        text = clean_html(response.text, max_chars=4000)
                        if len(text) > 100:
                            scraped.append({"url": page_url, "content": text})
                            page_regex = extract_regex_data(response.text)
                            merge_regex_data(all_regex_data, page_regex)
                            logger.info("scrape_internal_ok", url=page_url, chars=len(text))
            except Exception as e:
                logger.error("scrape_internal_error", url=page_url, error=str(e))

    logger.info("scrape_complete", pages_scraped=len(scraped), regex_keys=list(all_regex_data.keys()))

    return {
        "scraped_data": scraped,
        "regex_data": all_regex_data,
        "status": "extracting",
    }
