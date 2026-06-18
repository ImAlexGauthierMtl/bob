"""Opportunity HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.use_cases.opportunity_use_cases import OpportunityUseCases
from app.domain.exceptions import OpportunityLineItemNotFoundError, OpportunityNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_opportunity_use_cases
from app.presentation.schemas.opportunity_schemas import (
    OpportunityCreate, OpportunityUpdate, OpportunityResponse, OpportunityListResponse,
    OpportunityProductCreate, OpportunityProductResponse,
)

router = APIRouter(prefix="/api/v1/opportunities")


@router.get("", response_model=OpportunityListResponse)
async def list_opportunities(
    skip: int = 0, limit: int = 50,
    organization_id: str = Query(None), stage: str = Query(None),
    user: dict = Depends(get_current_user),
    use_cases: OpportunityUseCases = Depends(get_opportunity_use_cases),
):
    result = await use_cases.list_opportunities(
        user["tenant_id"],
        skip,
        limit,
        organization_id,
        stage,
    )
    return OpportunityListResponse(
        items=[OpportunityResponse.model_validate(opp) for opp in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    data: OpportunityCreate,
    user: dict = Depends(get_current_user),
    use_cases: OpportunityUseCases = Depends(get_opportunity_use_cases),
):
    created = await use_cases.create_opportunity(data.model_dump(), user)
    return OpportunityResponse.model_validate(created)


@router.get("/{opp_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opp_id: str,
    user: dict = Depends(get_current_user),
    use_cases: OpportunityUseCases = Depends(get_opportunity_use_cases),
):
    try:
        opp = await use_cases.get_opportunity(opp_id, user["tenant_id"])
    except OpportunityNotFoundError:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return OpportunityResponse.model_validate(opp)


@router.patch("/{opp_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opp_id: str, data: OpportunityUpdate,
    user: dict = Depends(get_current_user),
    use_cases: OpportunityUseCases = Depends(get_opportunity_use_cases),
):
    try:
        updated = await use_cases.update_opportunity(
            opp_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except OpportunityNotFoundError:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return OpportunityResponse.model_validate(updated)


@router.delete("/{opp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(
    opp_id: str,
    user: dict = Depends(get_current_user),
    use_cases: OpportunityUseCases = Depends(get_opportunity_use_cases),
):
    try:
        await use_cases.delete_opportunity(opp_id, user)
    except OpportunityNotFoundError:
        raise HTTPException(status_code=404, detail="Opportunity not found")


# ── Line items (OpportunityProduct) ──────────────────
@router.get("/{opp_id}/products", response_model=list[OpportunityProductResponse])
async def list_opp_products(
    opp_id: str,
    user: dict = Depends(get_current_user),
    use_cases: OpportunityUseCases = Depends(get_opportunity_use_cases),
):
    lines = await use_cases.list_products(opp_id, user["tenant_id"])
    return [OpportunityProductResponse.model_validate(line) for line in lines]


@router.post("/{opp_id}/products", response_model=OpportunityProductResponse, status_code=status.HTTP_201_CREATED)
async def add_opp_product(
    opp_id: str, data: OpportunityProductCreate,
    user: dict = Depends(get_current_user),
    use_cases: OpportunityUseCases = Depends(get_opportunity_use_cases),
):
    try:
        line = await use_cases.add_product(opp_id, data.model_dump(), user)
    except OpportunityNotFoundError:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return OpportunityProductResponse.model_validate(line)


@router.delete("/{opp_id}/products/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_opp_product(
    opp_id: str, line_id: str,
    user: dict = Depends(get_current_user),
    use_cases: OpportunityUseCases = Depends(get_opportunity_use_cases),
):
    try:
        await use_cases.remove_product(line_id, user["tenant_id"])
    except OpportunityLineItemNotFoundError:
        raise HTTPException(status_code=404, detail="Line item not found")
