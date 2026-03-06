"""Enrichment routes — AI-powered organization enrichment.

Based on `router-crud` template (RULED).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.application.use_cases.enrich_organization import EnrichOrganizationUseCase
from app.presentation.schemas.enrichment_schemas import EnrichmentStatusResponse

router = APIRouter(prefix="/api/v1/organizations")


@router.post("/{org_id}/enrich", response_model=EnrichmentStatusResponse)
async def enrich_organization(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger AI enrichment for an organization.

    Runs the LangGraph pipeline: search → scrape → extract → persist.
    """
    use_case = EnrichOrganizationUseCase(db)
    result = await use_case.execute(
        org_id=org_id,
        tenant_id=current_user["tenant_id"],
        user_email=current_user["email"],
    )

    if result["status"] == "error" and result.get("error") == "Organization not found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    return EnrichmentStatusResponse(
        organization_id=org_id,
        status=result["status"],
        fields_updated=result["fields_updated"],
        fields=result.get("fields", {}),
        error=result.get("error"),
    )
