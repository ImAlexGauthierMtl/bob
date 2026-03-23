"""Event CRUD routes — pure storage, no business logic."""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.ms365_repository import MS365Repository
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
    db: Session = Depends(get_db),
):
    """List synced calendar events for a user."""
    repo = MS365Repository(db)
    items = repo.list_events(user_id, current_user["tenant_id"], skip, limit, from_date, to_date)
    total = repo.count_events(user_id, current_user["tenant_id"], from_date, to_date)
    return EventListResponse(
        items=[EventResponse.model_validate(e) for e in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific synced event."""
    repo = MS365Repository(db)
    event = repo.get_event_by_id(event_id, user_id, current_user["tenant_id"])
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventResponse.model_validate(event)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def upsert_event(
    data: EventUpsertRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upsert (insert or update) a synced event."""
    repo = MS365Repository(db)
    event = repo.upsert_event(data.model_dump(), current_user["tenant_id"])
    return EventResponse.model_validate(event)


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    data: EventUpdateRequest,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update event metadata."""
    repo = MS365Repository(db)
    event = repo.get_event_by_id(event_id, user_id, current_user["tenant_id"])
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    updates = data.model_dump(exclude_unset=True)
    updated = repo.update_event(event, updates)
    return EventResponse.model_validate(updated)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hard-delete a synced event."""
    repo = MS365Repository(db)
    event = repo.get_event_by_id(event_id, user_id, current_user["tenant_id"])
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    repo.delete_event(event)
