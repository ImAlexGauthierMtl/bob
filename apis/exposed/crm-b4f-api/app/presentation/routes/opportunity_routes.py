"""Opportunity routes — proxies to opportunity~backend-api."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from app.infrastructure.clients.crm_clients import opportunity_client
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/opportunities")


@router.get("")
async def list_opportunities(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    organization_id: str = Query(None),
    stage: str = Query(None),
    user: dict = Depends(get_current_user),
):
    return await opportunity_client.list(skip, limit, organization_id, stage, forward_headers=request.headers)


@router.post("", status_code=201)
async def create_opportunity(data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await opportunity_client.create(data, forward_headers=request.headers)


@router.get("/{opp_id}")
async def get_opportunity(opp_id: str, request: Request, user: dict = Depends(get_current_user)):
    result = await opportunity_client.get(opp_id, forward_headers=request.headers)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result


@router.patch("/{opp_id}")
async def update_opportunity(opp_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await opportunity_client.update(opp_id, data, forward_headers=request.headers)


@router.delete("/{opp_id}", status_code=204)
async def delete_opportunity(opp_id: str, request: Request, user: dict = Depends(get_current_user)):
    await opportunity_client.delete(opp_id, forward_headers=request.headers)


# ── Line items (OpportunityProduct) ──────────────────
@router.get("/{opp_id}/products")
async def list_opp_products(opp_id: str, request: Request, user: dict = Depends(get_current_user)):
    return await opportunity_client.list_products(opp_id, forward_headers=request.headers)


@router.post("/{opp_id}/products", status_code=201)
async def add_opp_product(opp_id: str, data: dict, request: Request, user: dict = Depends(get_current_user)):
    return await opportunity_client.add_product(opp_id, data, forward_headers=request.headers)


@router.delete("/{opp_id}/products/{line_id}", status_code=204)
async def remove_opp_product(opp_id: str, line_id: str, request: Request, user: dict = Depends(get_current_user)):
    await opportunity_client.remove_product(opp_id, line_id, forward_headers=request.headers)
