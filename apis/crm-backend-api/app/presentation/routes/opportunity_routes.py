"""Opportunity routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.opportunity_repository import OpportunityRepository
from app.domain.entities.opportunity import Opportunity
from app.domain.entities.opportunity_product import OpportunityProduct
from app.presentation.schemas.crm_schemas import (
    OpportunityCreate, OpportunityUpdate, OpportunityResponse, OpportunityListResponse,
    OpportunityProductCreate, OpportunityProductResponse,
)

router = APIRouter(prefix="/api/v1/opportunities")

@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(skip: int = 0, limit: int = 50, organization_id: str = Query(None), stage: str = Query(None),
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OpportunityRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, organization_id, stage)
    total = repo.count(user["tenant_id"], organization_id)
    return OpportunityListResponse(items=[OpportunityResponse.model_validate(o) for o in items], total=total, skip=skip, limit=limit)

@router.post("", response_model=OpportunityResponse, status_code=201)
async def create_opportunity(data: OpportunityCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OpportunityRepository(db)
    opp = Opportunity(**data.model_dump(), tenant_id=user["tenant_id"], owner_id=user["user_id"], created_by=user["email"])
    return OpportunityResponse.model_validate(repo.create(opp))

@router.get("/{opp_id}", response_model=OpportunityResponse)
async def get_opportunity(opp_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, user["tenant_id"])
    if not opp: raise HTTPException(status_code=404, detail="Opportunity not found")
    return OpportunityResponse.model_validate(opp)

@router.patch("/{opp_id}", response_model=OpportunityResponse)
async def update_opportunity(opp_id: str, data: OpportunityUpdate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, user["tenant_id"])
    if not opp: raise HTTPException(status_code=404, detail="Opportunity not found")
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(opp, k, v)
    opp.updated_by = user["email"]
    return OpportunityResponse.model_validate(repo.update(opp))

@router.delete("/{opp_id}", status_code=204)
async def delete_opportunity(opp_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, user["tenant_id"])
    if not opp: raise HTTPException(status_code=404, detail="Opportunity not found")
    repo.soft_delete(opp, user["email"])

# ── Line items (OpportunityProduct) ──────────────────
@router.get("/{opp_id}/products", response_model=list[OpportunityProductResponse])
async def list_opp_products(opp_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OpportunityRepository(db)
    return [OpportunityProductResponse.model_validate(lp) for lp in repo.list_products(opp_id, user["tenant_id"])]

@router.post("/{opp_id}/products", response_model=OpportunityProductResponse, status_code=201)
async def add_opp_product(opp_id: str, data: OpportunityProductCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, user["tenant_id"])
    if not opp: raise HTTPException(status_code=404, detail="Opportunity not found")
    line = OpportunityProduct(opportunity_id=opp_id, tenant_id=user["tenant_id"], **data.model_dump())
    return OpportunityProductResponse.model_validate(repo.add_product(line))

@router.delete("/{opp_id}/products/{line_id}", status_code=204)
async def remove_opp_product(opp_id: str, line_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OpportunityRepository(db)
    line = repo.get_product_line(line_id, user["tenant_id"])
    if not line: raise HTTPException(status_code=404, detail="Line item not found")
    repo.remove_product(line)
