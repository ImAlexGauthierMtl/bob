"""Capability routes — B4F proxy to agent~backend-api.

Capability resolution logic stays in the backend. The B4F forwards requests.
"""

from fastapi import APIRouter, Depends, Request
from app.middleware.auth import get_current_user
from app.infrastructure.clients.agent_client import capability_client

router = APIRouter(prefix="/capabilities")


def _fh(request: Request) -> dict:
    return {"Authorization": request.headers.get("Authorization", "")}


@router.get("/catalog")
async def list_capability_catalog(request: Request, current_user: dict = Depends(get_current_user)):
    return await capability_client.list_catalog(forward_headers=_fh(request))


@router.get("/users/{user_id}")
async def get_user_capabilities(user_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await capability_client.get_user_capabilities(user_id, forward_headers=_fh(request))


@router.get("/me")
async def get_my_capabilities(request: Request, current_user: dict = Depends(get_current_user)):
    return await capability_client.get_my_capabilities(forward_headers=_fh(request))


@router.post("/users/{user_id}/assign", status_code=201)
async def assign_capability(user_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await capability_client.assign(user_id, data, forward_headers=_fh(request))


@router.post("/check")
async def check_capability(capability_code: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await capability_client.check(capability_code, forward_headers=_fh(request))
