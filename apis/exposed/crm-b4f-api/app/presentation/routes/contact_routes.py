"""Contact routes — proxies to contact~backend-api."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.crm_clients import contact_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/contacts")


@router.get("")
async def list_contacts(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    search: str = Query(None),
    organization_id: str = Query(None),
    user: dict = Depends(get_current_user),
):
    return await contact_client.list(skip, limit, search, organization_id, forward_headers=request.headers)


@router.post("", status_code=201)
async def create_contact(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await contact_client.create(data, forward_headers=request.headers)


@router.get("/{contact_id}")
async def get_contact(contact_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await contact_client.get(contact_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")
    return result


@router.patch("/{contact_id}")
async def update_contact(contact_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await contact_client.update(contact_id, data, forward_headers=request.headers)


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: str, request: Request, user: dict = Depends(get_current_user)):
    await contact_client.delete(contact_id, forward_headers=request.headers)
