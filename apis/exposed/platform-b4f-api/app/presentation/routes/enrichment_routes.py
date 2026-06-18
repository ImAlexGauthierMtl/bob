"""Enrichment routes — placeholder for enrichment B4F logic.

Enrichment is a B4F-only concern that orchestrates scraping + AI extraction.
In future phases this will call org~backend-api for organization data
and use AI services directly. For now, kept as a placeholder.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/organizations")


@router.post("/{org_id}/enrich")
async def enrich_organization(
    org_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    return {
        "organization_id": org_id,
        "status": "not_implemented",
        "message": "Enrichment pipeline not yet migrated to 3-tier architecture",
    }


@router.get("/{org_id}/enrich/status")
async def get_enrichment_status(
    org_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    return {
        "organization_id": org_id,
        "status": "not_implemented",
        "message": "Enrichment pipeline not yet migrated to 3-tier architecture",
    }
