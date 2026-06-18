"""Organization routes — proxies to org~backend-api."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.crm_clients import org_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/organizations")


@router.get("")
async def list_organizations(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    search: str = Query(None),
    user: dict = Depends(get_current_user),
):
    return await org_client.list(skip, limit, search, forward_headers=request.headers)


@router.post("", status_code=201)
async def create_organization(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await org_client.create(data, forward_headers=request.headers)


@router.get("/{org_id}")
async def get_organization(org_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await org_client.get(org_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Organization not found")
    return result


@router.patch("/{org_id}")
async def update_organization(org_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await org_client.update(org_id, data, forward_headers=request.headers)


@router.delete("/{org_id}", status_code=204)
async def delete_organization(org_id: str, request: Request, user: dict = Depends(get_current_user)):
    await org_client.delete(org_id, forward_headers=request.headers)
