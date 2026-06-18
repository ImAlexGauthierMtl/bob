"""Client Map 360° routes — CRUD for Client Map, Golden Notes, MEDDPICC score."""

from fastapi import APIRouter, Depends, HTTPException

from app.application.use_cases.client_map_use_cases import ClientMapUseCases
from app.domain.exceptions import ClientMapNotFoundError, ContactNotFoundError, GoldenNoteNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_client_map_use_cases
from app.presentation.schemas.client_map_schemas import (
    ClientMapUpsert, ClientMapResponse,
    GoldenNoteCreate, GoldenNoteUpdate, GoldenNoteResponse,
    MeddpiccScoreDetail,
)

router = APIRouter(prefix="/api/v1/contacts/{contact_id}/client-map")


@router.get("", response_model=ClientMapResponse)
async def get_client_map(
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: ClientMapUseCases = Depends(get_client_map_use_cases),
):
    try:
        return await use_cases.get_client_map(contact_id, current_user)
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")
    except ClientMapNotFoundError:
        raise HTTPException(status_code=404, detail="Client Map not found for this contact")


@router.put("", response_model=ClientMapResponse)
async def upsert_client_map(
    contact_id: str,
    payload: ClientMapUpsert,
    current_user: dict = Depends(get_current_user),
    use_cases: ClientMapUseCases = Depends(get_client_map_use_cases),
):
    try:
        return await use_cases.upsert_client_map(contact_id, payload.model_dump(exclude_unset=True), current_user)
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")


@router.post("/golden-notes", response_model=GoldenNoteResponse, status_code=201)
async def create_golden_note(
    contact_id: str,
    payload: GoldenNoteCreate,
    current_user: dict = Depends(get_current_user),
    use_cases: ClientMapUseCases = Depends(get_client_map_use_cases),
):
    try:
        return await use_cases.create_golden_note(contact_id, payload.model_dump(), current_user)
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")


@router.put("/golden-notes/{note_id}", response_model=GoldenNoteResponse)
async def update_golden_note(
    contact_id: str, note_id: str, payload: GoldenNoteUpdate,
    current_user: dict = Depends(get_current_user),
    use_cases: ClientMapUseCases = Depends(get_client_map_use_cases),
):
    try:
        return await use_cases.update_golden_note(contact_id, note_id, payload.model_dump(exclude_unset=True), current_user)
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")
    except GoldenNoteNotFoundError:
        raise HTTPException(status_code=404, detail="Golden Note not found")


@router.delete("/golden-notes/{note_id}", status_code=204)
async def delete_golden_note(
    contact_id: str, note_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: ClientMapUseCases = Depends(get_client_map_use_cases),
):
    try:
        await use_cases.delete_golden_note(contact_id, note_id, current_user)
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")
    except GoldenNoteNotFoundError:
        raise HTTPException(status_code=404, detail="Golden Note not found")


@router.get("/meddpicc-score", response_model=MeddpiccScoreDetail)
async def get_meddpicc_score(
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: ClientMapUseCases = Depends(get_client_map_use_cases),
):
    try:
        return await use_cases.get_meddpicc_score(contact_id, current_user)
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")
    except ClientMapNotFoundError:
        raise HTTPException(status_code=404, detail="Client Map not found for this contact")
