"""Hunter.io node — Domain Search + Company Enrichment before web scraping.

Calls Hunter.io APIs to identify contacts and enrich company data
BEFORE the scraper node runs. Gracefully skips if no API key is configured.
"""

from urllib.parse import urlparse

import httpx
import structlog

from app.config import settings
from app.agents.state import EnrichmentState
from app.infrastructure.database import SessionLocal
from app.middleware.usage_tracker import UsageTracker
from app.domain.entities.usage_transaction import TriggerSource

logger = structlog.get_logger(__name__)

HUNTER_BASE_URL = "https://api.hunter.io/v2"


def _extract_domain(url: str | None) -> str | None:
    """Extract clean domain from a URL (e.g. 'https://www.stripe.com/about' → 'stripe.com')."""
    if not url:
        return None
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        domain = parsed.netloc or parsed.path.split("/")[0]
        # Strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


async def hunter_node(state: EnrichmentState) -> dict:
    """Fetch contacts and company data from Hunter.io.

    Two API calls:
    1. Domain Search → contacts with emails, positions, LinkedIn
    2. Company Enrichment → industry, location, social, tech stack

    Gracefully skips if:
    - No Hunter API key configured
    - No website URL available (no domain to search)
    - API errors (pipeline continues without Hunter data)
    """
    api_key = settings.hunter_api_key
    if not api_key:
        logger.info("hunter_skip_no_api_key")
        return {"hunter_contacts": [], "hunter_company": {}, "status": "scraping"}

    # Extract domain from website URL
    urls = state.get("urls_to_scrape", [])
    website_url = urls[0] if urls else None
    domain = _extract_domain(website_url)

    if not domain:
        logger.info("hunter_skip_no_domain", organization=state.get("organization_name"))
        return {"hunter_contacts": [], "hunter_company": {}, "status": "scraping"}

    org_name = state.get("organization_name", "")
    tenant_id = state.get("tenant_id", "default")
    user_email = state.get("user_email", "")

    logger.info("hunter_start", organization=org_name, domain=domain)

    hunter_contacts: list[dict] = []
    hunter_company: dict = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        # ── 1. Domain Search — find contacts ──────────────────
        try:
            response = await client.get(
                f"{HUNTER_BASE_URL}/domain-search",
                params={"domain": domain, "api_key": api_key},
            )
            response.raise_for_status()
            data = response.json()

            emails = data.get("data", {}).get("emails", [])
            for contact in emails:
                hunter_contacts.append({
                    "email": contact.get("value"),
                    "first_name": contact.get("first_name"),
                    "last_name": contact.get("last_name"),
                    "position": contact.get("position"),
                    "position_raw": contact.get("position_raw"),
                    "seniority": contact.get("seniority"),
                    "department": contact.get("department"),
                    "linkedin": contact.get("linkedin"),
                    "phone": contact.get("phone_number"),
                    "confidence": contact.get("confidence"),
                    "verification_status": contact.get("verification", {}).get("status"),
                })

            logger.info("hunter_domain_search_done", domain=domain, contacts=len(hunter_contacts))

            # Track usage
            _track_usage(tenant_id, user_email, "domain-search", {"domain": domain, "contacts": len(hunter_contacts)})

        except Exception as e:
            logger.error("hunter_domain_search_error", domain=domain, error=str(e))

        # ── 2. Company Enrichment — company data ─────────────
        try:
            response = await client.get(
                f"{HUNTER_BASE_URL}/companies/find",
                params={"domain": domain, "api_key": api_key},
            )
            response.raise_for_status()
            data = response.json()

            company = data.get("data", {})
            if company:
                hunter_company = {
                    "name": company.get("name"),
                    "description": company.get("description"),
                    "industry": company.get("category", {}).get("industry"),
                    "sector": company.get("category", {}).get("sector"),
                    "sub_industry": company.get("category", {}).get("subIndustry"),
                    "tags": company.get("tags", []),
                    "founded_year": company.get("foundedYear"),
                    "company_type": company.get("companyType"),
                    "location": company.get("location"),
                    "phone": company.get("phone"),
                    "employees": company.get("metrics", {}).get("employees"),
                    "annual_revenue": company.get("metrics", {}).get("estimatedAnnualRevenue"),
                    "geo": company.get("geo", {}),
                    "social": {
                        "linkedin": f"https://linkedin.com/{company['linkedin']['handle']}" if company.get("linkedin", {}).get("handle") else None,
                        "twitter": f"https://twitter.com/{company['twitter']['handle']}" if company.get("twitter", {}).get("handle") else None,
                        "facebook": f"https://facebook.com/{company['facebook']['handle']}" if company.get("facebook", {}).get("handle") else None,
                        "youtube": f"https://youtube.com/{company['youtube']['handle']}" if company.get("youtube", {}).get("handle") else None,
                    },
                    "tech_stack": company.get("tech", []),
                    "email_pattern": company.get("emailPattern"),
                }

            logger.info("hunter_company_enrichment_done", domain=domain, has_data=bool(hunter_company))

            # Track usage
            _track_usage(tenant_id, user_email, "company-enrichment", {"domain": domain, "has_data": bool(hunter_company)})

        except Exception as e:
            logger.error("hunter_company_enrichment_error", domain=domain, error=str(e))

    logger.info(
        "hunter_complete",
        organization=org_name,
        domain=domain,
        contacts=len(hunter_contacts),
        has_company=bool(hunter_company),
    )

    return {
        "hunter_contacts": hunter_contacts,
        "hunter_company": hunter_company,
        "status": "scraping",
    }


def _track_usage(tenant_id: str, user_email: str, model: str, metadata: dict) -> None:
    """Track Hunter.io API usage."""
    try:
        db = SessionLocal()
        tracker = UsageTracker(db)
        tracker.track_search(
            tenant_id=tenant_id,
            user_id="",
            user_email=user_email,
            provider="hunter",
            trigger_source=TriggerSource.ENRICHMENT,
            metadata=metadata,
        )
        db.commit()
        db.close()
    except Exception as e:
        logger.warning("hunter_track_error", error=str(e))
