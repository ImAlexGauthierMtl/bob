"""Department routes — proxies to org~backend-api (departments endpoint)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.infrastructure.clients.crm_clients import org_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/departments")


@router.get("")
async def list_departments(request: Request, user: dict = Depends(get_current_user)):
    return await org_client.list_departments(forward_headers=request.headers)


@router.post("", status_code=201)
async def create_department(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await org_client.create_department(data, forward_headers=request.headers)


@router.get("/{dept_id}")
async def get_department(dept_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await org_client.get_department(dept_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Department not found")
    return result


@router.patch("/{dept_id}")
async def update_department(dept_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await org_client.update_department(dept_id, data, forward_headers=request.headers)


@router.delete("/{dept_id}", status_code=204)
async def delete_department(dept_id: str, request: Request, user: dict = Depends(get_current_user)):
    await org_client.delete_department(dept_id, forward_headers=request.headers)
