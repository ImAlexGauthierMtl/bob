"""Tenant admin routes — super_admin authorization (B4F logic) + HTTPClient."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from app.presentation.routes.auth_routes import get_current_user
from app.infrastructure.clients.user_client import user_client, tenant_client
from app.presentation.schemas.tenant_schemas import TenantCreate, TenantUpdate, TenantResponse, TenantListResponse, TenantProvisionRequest
from shared.infrastructure import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin/tenants")

async def require_super_admin(request: Request, current_user: dict = Depends(get_current_user)):
    user_data = await user_client.get_by_id(current_user["user_id"], forward_headers=request.headers)
    if not user_data or not user_data.get("is_super_admin", False):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user

@router.get("/", response_model=TenantListResponse)
async def list_tenants(request: Request, search: str = None, status_filter: str = Query(None, alias="status"), skip: int = 0, limit: int = 50, _auth: dict = Depends(require_super_admin)):
    result = await tenant_client.list_tenants(search, status_filter, skip, limit, forward_headers=request.headers)
    return result

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, request: Request, _auth: dict = Depends(require_super_admin)):
    tenant = await tenant_client.get_by_id(tenant_id, forward_headers=request.headers)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant

@router.post("/", response_model=TenantResponse, status_code=201)
async def create_tenant(data: TenantCreate, request: Request, _auth: dict = Depends(require_super_admin)):
    created = await tenant_client.create(data.model_dump(), forward_headers=request.headers)
    return created

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(tenant_id: str, data: TenantUpdate, request: Request, _auth: dict = Depends(require_super_admin)):
    updated = await tenant_client.update(tenant_id, data.model_dump(exclude_unset=True), forward_headers=request.headers)
    return updated

@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(tenant_id: str, request: Request, _auth: dict = Depends(require_super_admin)):
    deleted = await tenant_client.delete(tenant_id, forward_headers=request.headers)
    if not deleted:
        raise HTTPException(status_code=404, detail="Tenant not found")

@router.post("/{tenant_id}/provision", status_code=201)
async def provision_tenant(tenant_id: str, data: TenantProvisionRequest, request: Request, _auth: dict = Depends(require_super_admin)):
    tenant = await tenant_client.get_by_id(tenant_id, forward_headers=request.headers)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    created_user = await user_client.create({
        "email": data.admin_email, "password": data.admin_password,
        "first_name": data.admin_first_name, "last_name": data.admin_last_name,
        "tenant_id": tenant_id, "role": "admin",
    }, forward_headers=request.headers)
    return {"message": "Tenant provisioned", "tenant_id": tenant_id, "admin_user_id": created_user["id"]}
