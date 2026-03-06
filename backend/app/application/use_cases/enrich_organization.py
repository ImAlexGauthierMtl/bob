"""Enrich organization use case — runs in background.

Maps already provides: name, address, phone, website, industry.
This use case scrapes the website + extracts deeper info with Groq.
Now also generates a comprehensive organization_profile with:
services/products, key people, social media, business details.
"""

from sqlalchemy.orm import Session
import structlog

from app.agents.enrichment_graph import run_enrichment
from app.infrastructure.persistence.organization_repository import OrganizationRepository

logger = structlog.get_logger(__name__)


class EnrichOrganizationUseCase:
    """Run the AI enrichment pipeline and persist results."""

    def __init__(self, db: Session):
        self.repo = OrganizationRepository(db)

    async def execute(self, org_id: str, tenant_id: str, user_email: str) -> dict:
        """Enrich an organization with AI-gathered data.

        Scrapes the org's website and uses Groq to extract:
        - Flat fields: description, employee_count, revenue, linkedin, etc.
        - Deep profile: services, contacts, social media, key people, business details.
        """
        org = self.repo.get_by_id(org_id, tenant_id)
        if not org:
            logger.error("enrichment_org_not_found", org_id=org_id)
            return {"status": "error", "error": "Organization not found", "fields_updated": 0, "fields": {}}

        # Use the website from Maps data for scraping
        website_url = org.website

        result = await run_enrichment(
            organization_id=org_id,
            organization_name=org.name,
            tenant_id=tenant_id,
            user_email=user_email,
            website_url=website_url,
        )

        if result.get("status") == "error":
            return {
                "status": "error",
                "error": result.get("error", "Unknown error"),
                "fields_updated": 0,
                "fields": {},
            }

        # ── Apply flat extracted fields — only fill empty fields ──
        extracted = result.get("extracted", {})
        updated_count = 0

        allowed_fields = [
            "industry", "website", "phone", "email",
            "address_street", "address_city", "address_state",
            "address_country", "address_postal_code",
            "employee_count", "annual_revenue", "description",
            "linkedin_url", "org_type",
        ]

        for field in allowed_fields:
            if field in extracted and extracted[field]:
                current_value = getattr(org, field, None)
                if not current_value:
                    setattr(org, field, extracted[field])
                    updated_count += 1

        # ── Save deep profile ──
        organization_profile = result.get("organization_profile", {})
        if organization_profile:
            org.organization_profile = organization_profile
            logger.info("deep_profile_saved", org_id=org_id, categories=list(organization_profile.keys()))

        org.ai_enriched = "Y"
        org.updated_by = f"ai-agent ({user_email})"

        self.repo.update(org)

        logger.info(
            "enrichment_persisted",
            org_id=org_id,
            org_name=org.name,
            fields_updated=updated_count,
            has_profile=bool(organization_profile),
        )

        return {
            "status": "done",
            "fields_updated": updated_count,
            "fields": extracted,
            "organization_profile": organization_profile,
            "error": None,
        }
