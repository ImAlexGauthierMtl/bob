"""Search routes — Serper Maps API for organization discovery.

Step 1 of the Add Organization flow:
User types a name → we search Google Maps → return structured results.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import httpx
import structlog

from app.config import settings
from app.presentation.routes.auth_routes import get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/search")

SERPER_URL = "https://google.serper.dev/maps"


class SearchRequest(BaseModel):
    """Search query from the user."""
    query: str


class PlaceResult(BaseModel):
    """A single Google Maps result."""
    title: str
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    industry_types: List[str] = []
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    thumbnail_url: Optional[str] = None
    place_id: Optional[str] = None


class SearchResponse(BaseModel):
    """Search results."""
    query: str
    results: List[PlaceResult]
    total: int


@router.post("/maps", response_model=SearchResponse)
async def search_maps(
    body: SearchRequest,
    current_user: dict = Depends(get_current_user),
):
    """Search Google Maps via Serper for organizations.

    Returns structured results with name, address, phone, industry, etc.
    """
    query = body.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    logger.info("maps_search_start", query=query, user=current_user["email"])

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                SERPER_URL,
                json={"q": query, "num": 10},
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()

        places = []
        for place in data.get("places", []):
            places.append(PlaceResult(
                title=place.get("title", ""),
                address=place.get("address", ""),
                phone=place.get("phoneNumber"),
                website=place.get("website"),
                industry=place.get("type"),
                industry_types=place.get("types", []),
                rating=place.get("rating"),
                rating_count=place.get("ratingCount"),
                latitude=place.get("latitude"),
                longitude=place.get("longitude"),
                thumbnail_url=place.get("thumbnailUrl"),
                place_id=place.get("placeId"),
            ))

        logger.info("maps_search_done", query=query, results=len(places))

        return SearchResponse(
            query=query,
            results=places,
            total=len(places),
        )

    except httpx.HTTPStatusError as e:
        logger.error("maps_search_http_error", query=query, status=e.response.status_code)
        raise HTTPException(status_code=502, detail="Search service error")
    except Exception as e:
        logger.error("maps_search_error", query=query, error=str(e))
        raise HTTPException(status_code=500, detail="Search failed")
