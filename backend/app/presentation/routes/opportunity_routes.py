"""Opportunity routes — CRUD API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.middleware.authorization import require_permission
from app.domain.entities.opportunity import Opportunity
from app.infrastructure.persistence.opportunity_repository import OpportunityRepository
from app.presentation.schemas.opportunity_schemas import (
    OpportunityCreate, OpportunityUpdate, OpportunityResponse, OpportunityListResponse,
)
from app.presentation.schemas.opportunity_product_schemas import (
    OpportunityProductAdd, OpportunityProductResponse, OpportunityProductListResponse,
)
from app.domain.entities.opportunity_product import OpportunityProduct
from app.infrastructure.persistence.product_repository import ProductRepository

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


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("opportunity:write"))])
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
    resp = OpportunityResponse.model_validate(opp)
    if opp.organization:
        resp.organization_name = opp.organization.name
    if opp.contact:
        resp.contact_name = f"{opp.contact.first_name} {opp.contact.last_name}"
    return resp


@router.patch("/{opp_id}", response_model=OpportunityResponse,
              dependencies=[Depends(require_permission("opportunity:write"))])
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


@router.delete("/{opp_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("opportunity:delete"))])
async def delete_opportunity(
    opp_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, current_user["tenant_id"])
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    from app.middleware.dependency_guard import guard_delete
    guard_delete(db, "opportunities", opp_id, current_user["tenant_id"])
    repo.soft_delete(opp, current_user["email"])
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "opportunity.deleted", {"opportunity_id": opp_id}, db, current_user["tenant_id"], current_user["email"]
    ))


# ── Opportunity-Product endpoints ──────────────────────────


def _line_to_response(line) -> OpportunityProductResponse:
    """Convert an OpportunityProduct ORM instance to response schema."""
    return OpportunityProductResponse(
        id=line.id,
        opportunity_id=line.opportunity_id,
        product_id=line.product_id,
        quantity=line.quantity,
        unit_price=float(line.unit_price),
        discount_percent=float(line.discount_percent) if line.discount_percent else None,
        notes=line.notes,
        product_name=line.product.name if line.product else "",
        product_category=line.product.category.value if line.product else "",
        product_sku=line.product.sku if line.product else None,
        created_at=line.created_at,
    )


@router.get("/{opp_id}/products", response_model=OpportunityProductListResponse)
async def list_opportunity_products(
    opp_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, current_user["tenant_id"])
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    items = repo.list_products(opp_id, current_user["tenant_id"])
    return OpportunityProductListResponse(
        items=[_line_to_response(i) for i in items],
        total=len(items),
    )


@router.post("/{opp_id}/products", response_model=OpportunityProductResponse, status_code=status.HTTP_201_CREATED)
async def add_product_to_opportunity(
    opp_id: str,
    data: OpportunityProductAdd,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tenant_id = current_user["tenant_id"]
    repo = OpportunityRepository(db)
    opp = repo.get_by_id(opp_id, tenant_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    # Resolve product and snapshot price
    prod_repo = ProductRepository(db)
    product = prod_repo.get_by_id(data.product_id, tenant_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    line = OpportunityProduct(
        opportunity_id=opp_id,
        product_id=data.product_id,
        quantity=data.quantity,
        unit_price=product.unit_price,
        discount_percent=data.discount_percent,
        notes=data.notes,
        tenant_id=tenant_id,
        created_by=current_user["email"],
    )
    created = repo.add_product(line)
    return _line_to_response(created)


@router.delete("/{opp_id}/products/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_product_from_opportunity(
    opp_id: str,
    line_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = OpportunityRepository(db)
    line = repo.get_product_line(line_id, current_user["tenant_id"])
    if not line or line.opportunity_id != opp_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product line not found")
    repo.remove_product(line)
