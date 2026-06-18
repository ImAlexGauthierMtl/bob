"""Tenant HTTP routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.use_cases.tenant_use_cases import TenantUseCases
from app.domain.exceptions import TenantNotFoundError, TenantSlugAlreadyExistsError
from app.presentation.deps import get_tenant_use_cases
from app.presentation.schemas.tenant_schemas import (
    TenantCreateRequest, TenantUpdateRequest, TenantResponse, TenantListResponse,
)

router = APIRouter(prefix="/api/v1/tenants")

@router.get("", response_model=TenantListResponse)
async def list_tenants(
    search: Optional[str] = None, status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    use_cases: TenantUseCases = Depends(get_tenant_use_cases),
):
    result = await use_cases.list_tenants(search, status_filter, skip, limit)
    return TenantListResponse(items=[TenantResponse.model_validate(t) for t in result.items], total=result.total)

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    use_cases: TenantUseCases = Depends(get_tenant_use_cases),
):
    try:
        tenant = await use_cases.get_tenant(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)

@router.get("/by-slug/{slug}", response_model=TenantResponse)
async def get_tenant_by_slug(
    slug: str,
    use_cases: TenantUseCases = Depends(get_tenant_use_cases),
):
    try:
        tenant = await use_cases.get_tenant_by_slug(slug)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)

@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(
    data: TenantCreateRequest,
    use_cases: TenantUseCases = Depends(get_tenant_use_cases),
):
    try:
        tenant = await use_cases.create_tenant(data.model_dump())
    except TenantSlugAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Slug already in use")
    return TenantResponse.model_validate(tenant)

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    data: TenantUpdateRequest,
    use_cases: TenantUseCases = Depends(get_tenant_use_cases),
):
    try:
        updated = await use_cases.update_tenant(tenant_id, data.model_dump(exclude_unset=True))
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    except TenantSlugAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Slug already in use")
    return TenantResponse.model_validate(updated)

@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(
    tenant_id: str,
    use_cases: TenantUseCases = Depends(get_tenant_use_cases),
):
    try:
        await use_cases.delete_tenant(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
