"""Organization HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.use_cases.organization_use_cases import OrganizationUseCases
from app.domain.exceptions import OrganizationNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_organization_use_cases
from app.presentation.schemas.organization_schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationListResponse,
)

router = APIRouter(prefix="/api/v1/organizations")


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    skip: int = 0, limit: int = 50, search: str = Query(None),
    user: dict = Depends(get_current_user),
    use_cases: OrganizationUseCases = Depends(get_organization_use_cases),
):
    result = await use_cases.list_organizations(user["tenant_id"], skip, limit, search)
    return OrganizationListResponse(
        items=[OrganizationResponse.model_validate(org) for org in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    user: dict = Depends(get_current_user),
    use_cases: OrganizationUseCases = Depends(get_organization_use_cases),
):
    created = await use_cases.create_organization(data.model_dump(), user)
    return OrganizationResponse.model_validate(created)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    user: dict = Depends(get_current_user),
    use_cases: OrganizationUseCases = Depends(get_organization_use_cases),
):
    try:
        org = await use_cases.get_organization(org_id, user["tenant_id"])
    except OrganizationNotFoundError:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str, data: OrganizationUpdate,
    user: dict = Depends(get_current_user),
    use_cases: OrganizationUseCases = Depends(get_organization_use_cases),
):
    try:
        updated = await use_cases.update_organization(
            org_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except OrganizationNotFoundError:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse.model_validate(updated)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    user: dict = Depends(get_current_user),
    use_cases: OrganizationUseCases = Depends(get_organization_use_cases),
):
    try:
        await use_cases.delete_organization(org_id, user)
    except OrganizationNotFoundError:
        raise HTTPException(status_code=404, detail="Organization not found")
