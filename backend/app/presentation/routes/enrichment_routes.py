"""Enrichment routes — background AI enrichment.

Runs scraping + Groq extraction as a background task
so the user isn't blocked waiting.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db, SessionLocal
from app.presentation.routes.auth_routes import get_current_user
from app.application.use_cases.enrich_organization import EnrichOrganizationUseCase
from app.presentation.schemas.enrichment_schemas import EnrichmentStatusResponse

router = APIRouter(prefix="/api/v1/organizations")


async def _run_enrichment_background(org_id: str, tenant_id: str, user_email: str):
    """Run enrichment in the background using a dedicated DB session."""
    import structlog
    logger = structlog.get_logger(__name__)

    try:
        db = SessionLocal()
        use_case = EnrichOrganizationUseCase(db)
        result = await use_case.execute(
            org_id=org_id,
            tenant_id=tenant_id,
            user_email=user_email,
        )
        logger.info(
            "background_enrichment_done",
            org_id=org_id,
            status=result["status"],
            fields_updated=result["fields_updated"],
        )
    except Exception as e:
        logger.error("background_enrichment_error", org_id=org_id, error=str(e))
    finally:
        db.close()


@router.post("/{org_id}/enrich", response_model=EnrichmentStatusResponse)
async def enrich_organization(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger AI enrichment for an organization (background).

    Returns immediately with status "enriching".
    The actual scraping + Groq extraction runs in the background.
    """
    from app.infrastructure.persistence.organization_repository import OrganizationRepository
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id, current_user["tenant_id"])

    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    # Fire and forget — enrichment runs in background
    asyncio.create_task(
        _run_enrichment_background(
            org_id=org_id,
            tenant_id=current_user["tenant_id"],
            user_email=current_user["email"],
        )
    )

    return EnrichmentStatusResponse(
        organization_id=org_id,
        status="enriching",
        fields_updated=0,
        fields={},
        error=None,
    )
