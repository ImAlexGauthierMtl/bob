"""Activity routes — proxies to activity~backend-api."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.crm_clients import activity_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/activities")


@router.get("")
async def list_activities(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    organization_id: str = Query(None),
    contact_id: str = Query(None),
    opportunity_id: str = Query(None),
    status: str = Query(None),
    user: dict = Depends(get_current_user),
):
    return await activity_client.list(skip, limit, organization_id, contact_id, opportunity_id, status, forward_headers=request.headers)


@router.post("", status_code=201)
async def create_activity(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await activity_client.create(data, forward_headers=request.headers)


@router.get("/{activity_id}")
async def get_activity(activity_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await activity_client.get(activity_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Activity not found")
    return result


@router.patch("/{activity_id}")
async def update_activity(activity_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await activity_client.update(activity_id, data, forward_headers=request.headers)


@router.delete("/{activity_id}", status_code=204)
async def delete_activity(activity_id: str, request: Request, user: dict = Depends(get_current_user)):
    await activity_client.delete(activity_id, forward_headers=request.headers)
