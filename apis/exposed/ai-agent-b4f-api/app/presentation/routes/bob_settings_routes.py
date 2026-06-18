"""Bob settings routes — B4F proxy to agent~backend-api."""

from fastapi import APIRouter, Depends, Request
from app.middleware.auth import get_current_user
from app.infrastructure.clients.agent_client import bob_settings_client

router = APIRouter(prefix="/bob/settings")


def _fh(request: Request) -> dict:
    return {"Authorization": request.headers.get("Authorization", "")}


@router.get("")
async def get_bob_settings(request: Request, current_user: dict = Depends(get_current_user)):
    return await bob_settings_client.get(forward_headers=_fh(request))


@router.put("")
async def update_bob_settings(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await bob_settings_client.update(data, forward_headers=_fh(request))


@router.delete("", status_code=204)
async def reset_bob_settings(request: Request, current_user: dict = Depends(get_current_user)):
    await bob_settings_client.reset(forward_headers=_fh(request))
