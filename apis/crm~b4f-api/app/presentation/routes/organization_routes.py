"""Organization routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.organization_repository import OrganizationRepository
from app.domain.entities.organization import Organization
from app.presentation.schemas.crm_schemas import OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationListResponse

router = APIRouter(prefix="/api/v1/organizations")

@router.get("", response_model=OrganizationListResponse)
async def list_organizations(skip: int = 0, limit: int = 50, search: str = Query(None),
                              user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OrganizationRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, search)
    total = repo.count(user["tenant_id"])
    return OrganizationListResponse(items=[OrganizationResponse.model_validate(o) for o in items], total=total, skip=skip, limit=limit)

@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(data: OrganizationCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OrganizationRepository(db)
    org = Organization(**data.model_dump(), tenant_id=user["tenant_id"], owner_id=user["user_id"], created_by=user["email"])
    return OrganizationResponse.model_validate(repo.create(org))

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id, user["tenant_id"])
    if not org: raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse.model_validate(org)

@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(org_id: str, data: OrganizationUpdate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id, user["tenant_id"])
    if not org: raise HTTPException(status_code=404, detail="Organization not found")
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(org, k, v)
    org.updated_by = user["email"]
    return OrganizationResponse.model_validate(repo.update(org))

@router.delete("/{org_id}", status_code=204)
async def delete_organization(org_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = OrganizationRepository(db)
    org = repo.get_by_id(org_id, user["tenant_id"])
    if not org: raise HTTPException(status_code=404, detail="Organization not found")
    repo.soft_delete(org, user["email"])
