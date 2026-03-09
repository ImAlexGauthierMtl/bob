"""Activity routes — CRUD API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.middleware.authorization import require_permission
from app.domain.entities.activity import Activity
from app.infrastructure.persistence.activity_repository import ActivityRepository
from app.presentation.schemas.activity_schemas import (
    ActivityCreate, ActivityUpdate, ActivityResponse, ActivityListResponse,
)

router = APIRouter(prefix="/api/v1/activities")


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    organization_id: Optional[str] = None,
    contact_id: Optional[str] = None,
    opportunity_id: Optional[str] = None,
    activity_status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    items = repo.list_all(current_user["tenant_id"], skip, limit, organization_id, contact_id, opportunity_id, activity_status)
    total = repo.count(current_user["tenant_id"], organization_id, contact_id, opportunity_id, activity_status)
    return ActivityListResponse(
        items=[ActivityResponse.model_validate(a) for a in items],
        total=total, skip=skip, limit=limit,
    )


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("activity:write"))])
async def create_activity(
    data: ActivityCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    if not data.owner_id:
        data.owner_id = current_user["user_id"]
    activity = Activity(**data.model_dump(exclude_none=True), tenant_id=current_user["tenant_id"], created_by=current_user["email"])
    created = repo.create(activity)
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "activity.created", {"activity_id": created.id}, db, current_user["tenant_id"], current_user["email"]
    ))
    return ActivityResponse.model_validate(created)


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    activity = repo.get_by_id(activity_id, current_user["tenant_id"])
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    return ActivityResponse.model_validate(activity)


@router.patch("/{activity_id}", response_model=ActivityResponse,
              dependencies=[Depends(require_permission("activity:write"))])
async def update_activity(
    activity_id: str,
    data: ActivityUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    activity = repo.get_by_id(activity_id, current_user["tenant_id"])
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(activity, k, v)
    activity.updated_by = current_user["email"]
    updated = repo.update(activity)
    import asyncio
    from app.agents.event_bus import event_bus
    # Fire both updated and completed events (for meeting follow-up templates)
    asyncio.ensure_future(event_bus.publish(
        "activity.updated", {"activity_id": activity_id}, db, current_user["tenant_id"], current_user["email"]
    ))
    if data.model_dump(exclude_none=True).get("status") == "completed":
        asyncio.ensure_future(event_bus.publish(
            "activity.completed", {"activity_id": activity_id}, db, current_user["tenant_id"], current_user["email"]
        ))
    return ActivityResponse.model_validate(updated)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("activity:delete"))])
async def delete_activity(
    activity_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    activity = repo.get_by_id(activity_id, current_user["tenant_id"])
    if not activity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found")
    repo.soft_delete(activity, current_user["email"])
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "activity.deleted", {"activity_id": activity_id}, db, current_user["tenant_id"], current_user["email"]
    ))
