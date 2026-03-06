"""Opportunity routes — CRUD API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.domain.entities.opportunity import Opportunity
from app.infrastructure.persistence.opportunity_repository import OpportunityRepository
from app.presentation.schemas.opportunity_schemas import (
    OpportunityCreate, OpportunityUpdate, OpportunityResponse, OpportunityListResponse,
)

router = APIRouter(prefix="/api/v1/opportunities")


@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    organization_id: Optional[str] = None,
    stage: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = OpportunityRepository(db)
    items = repo.list_all(current_user["tenant_id"], skip, limit, organization_id, stage)
    total = repo.count(current_user["tenant_id"], organization_id)
    return OpportunityListResponse(
        items=[OpportunityResponse.model_validate(o) for o in items],
        total=total, skip=skip, limit=limit,
    )


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    data: OpportunityCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = OpportunityRepository(db)
    opp = Opportunity(**data.model_dump(exclude_none=True), tenant_id=current_user["tenant_id"], created_by=current_user["email"])
    created = repo.create(opp)
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "opportunity.created", {"opportunity_id": created.id}, db, current_user["tenant_id"], current_user["email"]
    ))
    return OpportunityResponse.model_validate(created)


@router.get("/{opp_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opp_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, current_user["tenant_id"])
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return OpportunityResponse.model_validate(opp)


@router.patch("/{opp_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opp_id: str,
    data: OpportunityUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, current_user["tenant_id"])
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(opp, k, v)
    opp.updated_by = current_user["email"]
    updated = repo.update(opp)
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "opportunity.updated", {"opportunity_id": opp_id}, db, current_user["tenant_id"], current_user["email"]
    ))
    return OpportunityResponse.model_validate(updated)


@router.delete("/{opp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opp_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, current_user["tenant_id"])
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    repo.soft_delete(opp, current_user["email"])
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "opportunity.deleted", {"opportunity_id": opp_id}, db, current_user["tenant_id"], current_user["email"]
    ))
