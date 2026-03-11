"""Enrichment routes — background AI enrichment with run tracking.

Runs scraping + Groq extraction as a background task
so the user isn't blocked waiting. Each run is persisted
for auditability and status polling.
"""

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db, SessionLocal
from app.presentation.routes.auth_routes import get_current_user
from app.application.use_cases.enrich_organization import EnrichOrganizationUseCase
from app.presentation.schemas.enrichment_schemas import EnrichmentStatusResponse
from app.domain.entities.enrichment_run import EnrichmentRun

router = APIRouter(prefix="/api/v1/organizations")


async def _run_enrichment_background(org_id: str, tenant_id: str, user_email: str, run_id: str):
    """Run enrichment in the background using a dedicated DB session."""
    import structlog
    logger = structlog.get_logger(__name__)

    db = SessionLocal()
    try:
        use_case = EnrichOrganizationUseCase(db)
        result = await use_case.execute(
            org_id=org_id,
            tenant_id=tenant_id,
            user_email=user_email,
        )

        run = db.query(EnrichmentRun).filter(EnrichmentRun.id == run_id).first()
        if run:
            run.complete(
                status=result["status"],
                fields_updated=result["fields_updated"],
                error=result.get("error"),
                summary={"fields": list(result.get("fields", {}).keys())},
            )
            db.commit()

        logger.info(
            "background_enrichment_done",
            org_id=org_id,
            run_id=run_id,
            status=result["status"],
            fields_updated=result["fields_updated"],
        )

        try:
            from app.middleware.metrics import record_enrichment_run
            record_enrichment_run(result["status"])
        except Exception:
            pass
    except Exception as e:
        logger.error("background_enrichment_error", org_id=org_id, run_id=run_id, error=str(e))
        try:
            run = db.query(EnrichmentRun).filter(EnrichmentRun.id == run_id).first()
            if run:
                run.complete(status="error", error=str(e))
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/{org_id}/enrich", response_model=EnrichmentStatusResponse)
async def enrich_organization(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger AI enrichment for an organization (background).

    Returns immediately with status "enriching" and a run_id for polling.
    The actual scraping + Groq extraction runs in the background.
    """
    from app.infrastructure.persistence.organization_repository import OrganizationRepository
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id, current_user["tenant_id"])

    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    run = EnrichmentRun(
        organization_id=org_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    asyncio.create_task(
        _run_enrichment_background(
            org_id=org_id,
            tenant_id=current_user["tenant_id"],
            user_email=current_user["email"],
            run_id=run.id,
        )
    )

    return EnrichmentStatusResponse(
        organization_id=org_id,
        status="enriching",
        fields_updated=0,
        fields={},
        error=None,
        run_id=run.id,
    )


@router.get("/{org_id}/enrich/status", response_model=EnrichmentStatusResponse)
async def get_enrichment_status(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the latest enrichment run status for an organization."""
    run = (
        db.query(EnrichmentRun)
        .filter(
            EnrichmentRun.organization_id == org_id,
            EnrichmentRun.tenant_id == current_user["tenant_id"],
        )
        .order_by(EnrichmentRun.started_at.desc())
        .first()
    )

    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrichment run found")

    return EnrichmentStatusResponse(
        organization_id=org_id,
        status=run.status,
        fields_updated=run.fields_updated or 0,
        fields=run.result_summary or {},
        error=run.error,
        run_id=run.id,
    )
