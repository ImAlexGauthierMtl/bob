"""Organization routes — CRUD API."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.middleware.authorization import require_permission
from app.application.use_cases.organization_use_cases import (
    CreateOrganizationUseCase,
    ListOrganizationsUseCase,
    GetOrganizationUseCase,
    UpdateOrganizationUseCase,
    DeleteOrganizationUseCase,
)
from app.presentation.schemas.organization_schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListResponse,
)

router = APIRouter(prefix="/api/v1/organizations")


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List organizations (tenant-scoped)."""
    use_case = ListOrganizationsUseCase(db)
    result = use_case.execute(
        tenant_id=current_user["tenant_id"],
        skip=skip,
        limit=limit,
        search=search,
    )
    return OrganizationListResponse(
        items=[OrganizationResponse.model_validate(org) for org in result["items"]],
        total=result["total"],
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("organization:write"))])
async def create_organization(
    org_data: OrganizationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new organization."""
    use_case = CreateOrganizationUseCase(db)
    org = use_case.execute(
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
        **org_data.model_dump(exclude_none=True),
    )
    # Fire event for workflow triggers
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "organization.created", {"organization_id": org.id}, db, current_user["tenant_id"], current_user["email"]
    ))
    return OrganizationResponse.model_validate(org)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single organization."""
    use_case = GetOrganizationUseCase(db)
    org = use_case.execute(org_id, current_user["tenant_id"])
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrganizationResponse,
              dependencies=[Depends(require_permission("organization:write"))])
async def update_organization(
    org_id: str,
    org_data: OrganizationUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an organization."""
    use_case = UpdateOrganizationUseCase(db)
    org = use_case.execute(
        org_id=org_id,
        tenant_id=current_user["tenant_id"],
        updated_by=current_user["email"],
        **org_data.model_dump(exclude_none=True),
    )
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("organization:delete"))])
async def delete_organization(
    org_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete an organization."""
    use_case = DeleteOrganizationUseCase(db)
    deleted = use_case.execute(org_id, current_user["tenant_id"], current_user["email"])
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    # Fire event for workflow triggers
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "organization.deleted", {"organization_id": org_id}, db, current_user["tenant_id"], current_user["email"]
    ))
