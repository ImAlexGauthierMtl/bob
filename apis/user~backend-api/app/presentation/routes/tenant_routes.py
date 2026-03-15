"""Tenant CRUD routes — pure storage."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.tenant_repository import TenantRepository
from app.presentation.schemas.tenant_schemas import (
    TenantCreateRequest, TenantUpdateRequest, TenantResponse, TenantListResponse,
)

router = APIRouter(prefix="/api/v1/tenants")

@router.get("", response_model=TenantListResponse)
async def list_tenants(
    search: Optional[str] = None, status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    repo = TenantRepository(db)
    items, total = repo.get_all(search=search, status=status_filter, skip=skip, limit=limit)
    return TenantListResponse(items=[TenantResponse.model_validate(t) for t in items], total=total)

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, db: Session = Depends(get_db)):
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)

@router.get("/by-slug/{slug}", response_model=TenantResponse)
async def get_tenant_by_slug(slug: str, db: Session = Depends(get_db)):
    repo = TenantRepository(db)
    tenant = repo.get_by_slug(slug)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)

@router.post("", response_model=TenantResponse, status_code=201)
async def create_tenant(data: TenantCreateRequest, db: Session = Depends(get_db)):
    repo = TenantRepository(db)
    existing = repo.get_by_slug(data.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Slug already in use")
    tenant = repo.create(**data.model_dump())
    return TenantResponse.model_validate(tenant)

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: str, data: TenantUpdateRequest, db: Session = Depends(get_db)):
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if data.slug and data.slug != tenant.slug:
        existing = repo.get_by_slug(data.slug)
        if existing:
            raise HTTPException(status_code=409, detail="Slug already in use")
    updated = repo.update(tenant, **data.model_dump(exclude_unset=True))
    return TenantResponse.model_validate(updated)

@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(tenant_id: str, db: Session = Depends(get_db)):
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    repo.soft_delete(tenant)
