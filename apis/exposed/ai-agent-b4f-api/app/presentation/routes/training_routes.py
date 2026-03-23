"""Training routes — B4F proxy to agent~backend-api."""

from fastapi import APIRouter, Depends, Request
from app.middleware.auth import get_current_user
from app.infrastructure.clients.agent_client import training_client

router = APIRouter(prefix="/api/v1/training")


def _fh(request: Request) -> dict:
    return {"Authorization": request.headers.get("Authorization", "")}


@router.post("/sessions", status_code=201)
async def create_session(request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await training_client.create_session(data, forward_headers=_fh(request))


@router.patch("/sessions/{session_id}/slide")
async def update_slide(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await training_client.update_slide(session_id, data, forward_headers=_fh(request))


@router.get("/sessions/{session_id}/notes")
async def get_notes(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await training_client.get_notes(session_id, forward_headers=_fh(request))


@router.post("/sessions/{session_id}/notes", status_code=201)
async def create_note(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await training_client.create_note(session_id, data, forward_headers=_fh(request))


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(note_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await training_client.delete_note(note_id, forward_headers=_fh(request))


@router.get("/sessions/{session_id}/missing")
async def get_missing(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    return await training_client.get_missing(session_id, forward_headers=_fh(request))


@router.post("/sessions/{session_id}/missing", status_code=201)
async def create_missing(session_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await training_client.create_missing(session_id, data, forward_headers=_fh(request))


@router.delete("/missing/{item_id}", status_code=204)
async def delete_missing(item_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    await training_client.delete_missing(item_id, forward_headers=_fh(request))
