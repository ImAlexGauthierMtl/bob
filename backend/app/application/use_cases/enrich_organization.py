"""Enrich organization use case.

Based on `use-case` template (RULED).
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

        Returns:
            dict with status, fields_updated, and extracted fields
        """
        # Get the organization
        org = self.repo.get_by_id(org_id, tenant_id)
        if not org:
            return {"status": "error", "error": "Organization not found", "fields_updated": 0, "fields": {}}

        # Run the enrichment pipeline
        result = await run_enrichment(
            organization_id=org_id,
            organization_name=org.name,
            tenant_id=tenant_id,
            user_email=user_email,
        )

        if result.get("status") == "error":
            return {
                "status": "error",
                "error": result.get("error", "Unknown error"),
                "fields_updated": 0,
                "fields": {},
            }

        # Apply extracted fields to the organization
        extracted = result.get("extracted", {})
        updated_count = 0

        # Only update fields that are currently empty
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
                if not current_value:  # Only fill empty fields
                    setattr(org, field, extracted[field])
                    updated_count += 1

        # Mark as AI-enriched
        org.ai_enriched = "Y"
        org.updated_by = f"ai-agent ({user_email})"

        self.repo.update(org)

        logger.info(
            "enrichment_persisted",
            org_id=org_id,
            org_name=org.name,
            fields_updated=updated_count,
        )

        return {
            "status": "done",
            "fields_updated": updated_count,
            "fields": extracted,
            "error": None,
        }
