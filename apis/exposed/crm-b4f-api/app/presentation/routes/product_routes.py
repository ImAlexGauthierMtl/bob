"""Product routes — proxies to product~backend-api."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.crm_clients import product_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/products")


@router.get("")
async def list_products(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    category: str = Query(None),
    user: dict = Depends(get_current_user),
):
    return await product_client.list(skip, limit, category, forward_headers=request.headers)


@router.post("", status_code=201)
async def create_product(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await product_client.create(data, forward_headers=request.headers)


@router.get("/{product_id}")
async def get_product(product_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await product_client.get(product_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")
    return result


@router.patch("/{product_id}")
async def update_product(product_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await product_client.update(product_id, data, forward_headers=request.headers)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, request: Request, user: dict = Depends(get_current_user)):
    await product_client.delete(product_id, forward_headers=request.headers)
