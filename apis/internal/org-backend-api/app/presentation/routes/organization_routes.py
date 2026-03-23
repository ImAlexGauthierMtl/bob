"""Organization CRUD routes — pure storage, no business logic."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.organization_repository import OrganizationRepository
from app.domain.entities.organization import Organization
from app.events.publishers import publish_org_created, publish_org_updated, publish_org_deleted
from app.presentation.schemas.organization_schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationListResponse,
)

router = APIRouter(prefix="/api/v1/organizations")


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    skip: int = 0, limit: int = 50, search: str = Query(None),
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = OrganizationRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, search)
    total = repo.count(user["tenant_id"])
    return OrganizationListResponse(
        items=[OrganizationResponse.model_validate(o) for o in items],
        total=total, skip=skip, limit=limit,
    )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = OrganizationRepository(db)
    org = Organization(
        **data.model_dump(),
        tenant_id=user["tenant_id"],
        owner_id=user["user_id"],
        created_by=user["email"],
    )
    created = repo.create(org)
    await publish_org_created(created.id, {"name": created.name, "tenant_id": created.tenant_id})
    return OrganizationResponse.model_validate(created)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id, user["tenant_id"])
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str, data: OrganizationUpdate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id, user["tenant_id"])
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(org, k, v)
    org.updated_by = user["email"]
    updated = repo.update(org)
    await publish_org_updated(updated.id, {"fields": list(updates.keys())})
    return OrganizationResponse.model_validate(updated)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    org_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id, user["tenant_id"])
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    repo.soft_delete(org, user["email"])
    await publish_org_deleted(org_id)
