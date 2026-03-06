"""Enrichment schemas — Pydantic models.

Based on `schemas-pydantic` template (RULED).
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class EnrichmentRequest(BaseModel):
    """Request to enrich an organization."""
    pass  # No body needed — org ID is in the URL path


class EnrichmentStatusResponse(BaseModel):
    """Enrichment result status."""

    organization_id: str
    status: str  # "done" | "error"
    fields_updated: int
    fields: Dict[str, Any]
    error: Optional[str] = None


class SearchResultItem(BaseModel):
    """A single search result."""

    title: str
    link: str
    snippet: str


class EnrichmentDetailResponse(BaseModel):
    """Full enrichment result with details."""

    organization_id: str
    organization_name: str
    status: str
    search_results: List[SearchResultItem]
    pages_scraped: int
    fields_extracted: Dict[str, Any]
    error: Optional[str] = None
