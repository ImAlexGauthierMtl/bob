"""Tenant administration routes — super_admin only, cross-tenant."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.persistence.tenant_repository import TenantRepository
from app.infrastructure.persistence.user_repository import UserRepository
from app.presentation.routes.auth_routes import get_current_user
from app.presentation.schemas.tenant_schemas import (
    TenantCreate, TenantUpdate, TenantResponse, TenantListResponse, TenantProvisionRequest,
)
from app.domain.entities.user import User
from shared.infrastructure import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin/tenants")


def require_super_admin(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["user_id"]).first()
    if not user or not getattr(user, "is_super_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return current_user


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    search: str = Query(None), status_filter: str = Query(None, alias="status"),
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db), _auth: dict = Depends(require_super_admin),
):
    repo = TenantRepository(db)
    items, total = repo.get_all(search=search, status=status_filter, skip=skip, limit=limit)
    return TenantListResponse(items=[TenantResponse.model_validate(t) for t in items], total=total)


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_super_admin)):
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)


@router.post("/", response_model=TenantResponse, status_code=201)
async def create_tenant(data: TenantCreate, db: Session = Depends(get_db), _auth: dict = Depends(require_super_admin)):
    repo = TenantRepository(db)
    existing = repo.get_by_slug(data.slug)
    if existing:
        raise HTTPException(status_code=409, detail="Slug already in use")
    tenant = repo.create(**data.model_dump())
    return TenantResponse.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str, data: TenantUpdate,
    db: Session = Depends(get_db), _auth: dict = Depends(require_super_admin),
):
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
async def delete_tenant(tenant_id: str, db: Session = Depends(get_db), _auth: dict = Depends(require_super_admin)):
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    repo.soft_delete(tenant)


@router.post("/{tenant_id}/provision", response_model=dict, status_code=201)
async def provision_tenant(
    tenant_id: str, data: TenantProvisionRequest,
    db: Session = Depends(get_db), _auth: dict = Depends(require_super_admin),
):
    repo = TenantRepository(db)
    tenant = repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    user_repo = UserRepository(db)
    existing_user = user_repo.get_by_email(data.admin_email)
    if existing_user:
        raise HTTPException(status_code=409, detail="User with this email already exists")

    from app.infrastructure.seed_roles import seed_roles
    seed_roles(db, tenant.id)

    new_user = User(
        email=data.admin_email,
        password_hash=User.hash_password(data.admin_password),
        first_name=data.admin_first_name,
        last_name=data.admin_last_name,
        tenant_id=tenant.id,
        role="admin",
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    from app.domain.entities.role import Role, UserRole
    admin_role = db.query(Role).filter(Role.tenant_id == tenant.id, Role.name == "admin").first()
    if admin_role:
        existing_assignment = db.query(UserRole).filter(
            UserRole.user_id == new_user.id, UserRole.role_id == admin_role.id,
        ).first()
        if not existing_assignment:
            db.add(UserRole(user_id=new_user.id, role_id=admin_role.id))
            db.commit()

    logger.info("tenant_provisioned", tenant_id=tenant.id, admin_user_id=new_user.id)
    return {"message": "Tenant provisioned successfully", "tenant_id": tenant.id,
            "admin_user_id": new_user.id, "admin_email": new_user.email}
