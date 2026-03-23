"""Activity CRUD routes — pure storage, no business logic."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.activity_repository import ActivityRepository
from app.domain.entities.activity import Activity
from app.events.publishers import publish_activity_created, publish_activity_updated
from app.presentation.schemas.activity_schemas import (
    ActivityCreate, ActivityUpdate, ActivityResponse, ActivityListResponse,
)

router = APIRouter(prefix="/api/v1/activities")


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    skip: int = 0, limit: int = 50, status_filter: str = Query(None, alias="status"),
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, status_filter)
    total = repo.count(user["tenant_id"], status_filter)
    return ActivityListResponse(
        items=[ActivityResponse.model_validate(a) for a in items],
        total=total, skip=skip, limit=limit,
    )


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    data: ActivityCreate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    activity = Activity(
        subject=data.subject,
        description=data.description,
        activity_type=data.activity_type,
        priority=data.priority,
        status=data.status,
        due_date=data.due_date,
        organization_ids=data.organization_ids or [],
        contact_ids=data.contact_ids or [],
        opportunity_ids=data.opportunity_ids or [],
        assigned_to=data.assigned_to,
        owner_id=data.owner_id or user["user_id"],
        tenant_id=user["tenant_id"],
        created_by=user["email"],
    )
    created = repo.create(activity)
    await publish_activity_created(created.id, {"subject": created.subject, "tenant_id": created.tenant_id})
    return ActivityResponse.model_validate(created)


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    act = repo.get_by_id(activity_id, user["tenant_id"])
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    return ActivityResponse.model_validate(act)


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: str, data: ActivityUpdate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    act = repo.get_by_id(activity_id, user["tenant_id"])
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(act, k, v)
    act.updated_by = user["email"]
    updated = repo.update(act)
    await publish_activity_updated(updated.id, {"fields": list(updates.keys())})
    return ActivityResponse.model_validate(updated)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = ActivityRepository(db)
    act = repo.get_by_id(activity_id, user["tenant_id"])
    if not act:
        raise HTTPException(status_code=404, detail="Activity not found")
    repo.soft_delete(act, user["email"])
