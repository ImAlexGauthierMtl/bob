"""Quote routes — proxies to opportunity~backend-api (quotes endpoint)."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.crm_clients import opportunity_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/quotes")


@router.get("")
async def list_quotes(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    opportunity_id: str = Query(None),
    user: dict = Depends(get_current_user),
):
    return await opportunity_client.list_quotes(skip, limit, opportunity_id, forward_headers=request.headers)


@router.post("", status_code=201)
async def create_quote(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await opportunity_client.create_quote(data, forward_headers=request.headers)


@router.get("/{quote_id}")
async def get_quote(quote_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await opportunity_client.get_quote(quote_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Quote not found")
    return result


@router.patch("/{quote_id}")
async def update_quote(quote_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await opportunity_client.update_quote(quote_id, data, forward_headers=request.headers)


@router.delete("/{quote_id}", status_code=204)
async def delete_quote(quote_id: str, request: Request, user: dict = Depends(get_current_user)):
    await opportunity_client.delete_quote(quote_id, forward_headers=request.headers)
