"""Event CRUD routes — pure storage, no business logic."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.use_cases.ms365_core_use_cases import MS365CoreUseCases
from app.domain.exceptions import EventNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_ms365_core_use_cases
from app.presentation.schemas.ms365_schemas import (
    EventUpsertRequest,
    EventUpdateRequest,
    EventResponse,
    EventListResponse,
)

router = APIRouter(prefix="/api/v1/events")


@router.get("", response_model=EventListResponse)
async def list_events(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """List synced calendar events for a user."""
    result = await use_cases.list_events(user_id, current_user["tenant_id"], skip, limit, from_date, to_date)
    return EventListResponse(
        items=[EventResponse.model_validate(e) for e in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Get a specific synced event."""
    try:
        event = await use_cases.get_event(event_id, user_id, current_user["tenant_id"])
    except EventNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(event)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def upsert_event(
    data: EventUpsertRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Upsert (insert or update) a synced event."""
    event = await use_cases.upsert_event(data.model_dump(), current_user["tenant_id"])
    return EventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    data: EventUpdateRequest,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Update event metadata."""
    try:
        updated = await use_cases.update_event(
            event_id,
            user_id,
            current_user["tenant_id"],
            data.model_dump(exclude_unset=True),
        )
    except EventNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(updated)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Hard-delete a synced event."""
    try:
        await use_cases.delete_event(event_id, user_id, current_user["tenant_id"])
    except EventNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found")
