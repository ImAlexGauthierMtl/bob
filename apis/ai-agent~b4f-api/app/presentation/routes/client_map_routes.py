"""Client Map 360° routes — B4F proxy to agent~backend-api.

CRUD is delegated to the backend. Behavioral analysis (LLM) stays here.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from app.middleware.auth import get_current_user
from app.infrastructure.clients.agent_client import client_map_client

router = APIRouter(prefix="/api/v1/contacts/{contact_id}/client-map")


def _fh(request: Request) -> dict:
    return {"Authorization": request.headers.get("Authorization", "")}


@router.get("")
async def get_client_map(contact_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    result = await client_map_client.get(contact_id, forward_headers=_fh(request))
    if not result:
        raise HTTPException(status_code=404, detail="Client Map not found for this contact")
    return result


@router.put("")
async def upsert_client_map(contact_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await client_map_client.upsert(contact_id, data, forward_headers=_fh(request))


@router.post("/golden-notes", status_code=201)
async def create_golden_note(contact_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await client_map_client.create_golden_note(contact_id, data, forward_headers=_fh(request))


@router.put("/golden-notes/{note_id}")
async def update_golden_note(contact_id: str, note_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    data = await request.json()
    return await client_map_client.update_golden_note(contact_id, note_id, data, forward_headers=_fh(request))


@router.delete("/golden-notes/{note_id}", status_code=204)
async def delete_golden_note(contact_id: str, note_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    success = await client_map_client.delete_golden_note(contact_id, note_id, forward_headers=_fh(request))
    if not success:
        raise HTTPException(status_code=404, detail="Golden Note not found")


@router.get("/meddpicc-score")
async def get_meddpicc_score(contact_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    result = await client_map_client.get_meddpicc_score(contact_id, forward_headers=_fh(request))
    if not result:
        raise HTTPException(status_code=404, detail="Client Map not found for this contact")
    return result


@router.post("/analyze-behavior")
async def trigger_behavioral_analysis(
    contact_id: str, request: Request, current_user: dict = Depends(get_current_user),
):
    """Behavioral analysis — LLM business logic stays in B4F."""
    try:
        from app.application.use_cases.behavioral_analyzer import BehavioralAnalyzer
        analyzer = BehavioralAnalyzer(client_map_client)
        profile = await analyzer.analyze(
            contact_id=contact_id,
            tenant_id=current_user["tenant_id"],
            forward_headers=_fh(request),
        )
        return {"status": "ok", "behavioral_profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
