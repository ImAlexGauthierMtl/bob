"""Activity routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.activity_repository import ActivityRepository
from app.presentation.schemas.crm_schemas import ActivityCreate, ActivityUpdate, ActivityResponse, ActivityListResponse

router = APIRouter(prefix="/api/v1/activities")

def _activity_to_response(act) -> ActivityResponse:
    data = ActivityResponse.model_validate(act)
    data.organization_ids = [o.id for o in act.organizations] if act.organizations else []
    data.contact_ids = [c.id for c in act.contacts] if act.contacts else []
    data.opportunity_ids = [o.id for o in act.opportunities] if act.opportunities else []
    return data

@router.get("", response_model=ActivityListResponse)
async def list_activities(skip: int = 0, limit: int = 50, organization_id: str = Query(None),
                           contact_id: str = Query(None), opportunity_id: str = Query(None), status: str = Query(None),
                           user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ActivityRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, organization_id, contact_id, opportunity_id, status)
    total = repo.count(user["tenant_id"], organization_id, contact_id, opportunity_id, status)
    return ActivityListResponse(items=[_activity_to_response(a) for a in items], total=total, skip=skip, limit=limit)

@router.post("", response_model=ActivityResponse, status_code=201)
async def create_activity(data: ActivityCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ActivityRepository(db)
    payload = data.model_dump()
    payload["owner_id"] = payload.get("owner_id") or user["user_id"]
    act = repo.create(payload, user["tenant_id"])
    return _activity_to_response(act)

@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(activity_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ActivityRepository(db)
    act = repo.get_by_id(activity_id, user["tenant_id"])
    if not act: raise HTTPException(status_code=404, detail="Activity not found")
    return _activity_to_response(act)

@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(activity_id: str, data: ActivityUpdate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ActivityRepository(db)
    act = repo.get_by_id(activity_id, user["tenant_id"])
    if not act: raise HTTPException(status_code=404, detail="Activity not found")
    payload = data.model_dump(exclude_unset=True)
    simple_fields = {k: v for k, v in payload.items() if k not in ("organization_ids", "contact_ids", "opportunity_ids")}
    for k, v in simple_fields.items(): setattr(act, k, v)
    act.updated_by = user["email"]
    return _activity_to_response(repo.update(act, payload))

@router.delete("/{activity_id}", status_code=204)
async def delete_activity(activity_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ActivityRepository(db)
    act = repo.get_by_id(activity_id, user["tenant_id"])
    if not act: raise HTTPException(status_code=404, detail="Activity not found")
    repo.soft_delete(act, user["email"])
