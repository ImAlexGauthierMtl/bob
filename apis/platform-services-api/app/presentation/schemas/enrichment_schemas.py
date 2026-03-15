"""Enrichment Schemas."""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class EnrichmentRequest(BaseModel):
    """Request to enrich an organization."""
    org_id: str
    data: Optional[Dict[str, Any]] = None


class EnrichmentResponse(BaseModel):
    """Enrichment response."""
    org_id: str
    enriched_data: Dict[str, Any]
    status: str


class EnrichmentStatusResponse(BaseModel):
    """Enrichment status response."""
    org_id: str
    status: str
    progress: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
