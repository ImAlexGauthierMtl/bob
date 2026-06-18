"""Training routes — CRUD for training sessions, notes, and missing elements."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

import structlog

from app.application.use_cases.training_use_cases import TrainingUseCases
from app.domain.exceptions import (
    TrainingMissingElementNotFoundError,
    TrainingNoteNotFoundError,
    TrainingSessionNotFoundError,
)
from app.middleware.auth import get_current_user
from app.presentation.deps import get_training_use_cases

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/training")


# ── Schemas ──────────────────────────────────────

class CreateSessionRequest(BaseModel):
    training_slug: str


class SessionResponse(BaseModel):
    id: str
    user_id: str
    training_slug: str
    current_slide: int
    started_at: datetime

    class Config:
        from_attributes = True


class UpdateSlideRequest(BaseModel):
    current_slide: int


class CreateNoteRequest(BaseModel):
    slide_id: Optional[int] = None
    content: str
    note_type: str = "insight"


class NoteResponse(BaseModel):
    id: str
    session_id: str
    slide_id: Optional[int]
    content: str
    note_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class CreateMissingRequest(BaseModel):
    label: str
    category: str = "integration"
    description: Optional[str] = None


class MissingResponse(BaseModel):
    id: str
    session_id: str
    label: str
    category: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Session Routes ───────────────────────────────

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: TrainingUseCases = Depends(get_training_use_cases),
):
    session = await use_cases.create_session(request.training_slug, current_user)
    logger.info("training_session_created", session_id=session.id, slug=request.training_slug)
    return session


@router.patch("/sessions/{session_id}/slide")
async def update_slide(
    session_id: str,
    request: UpdateSlideRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: TrainingUseCases = Depends(get_training_use_cases),
):
    try:
        return await use_cases.update_slide(session_id, request.current_slide, current_user)
    except TrainingSessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")


# ── Note Routes ──────────────────────────────────

@router.get("/sessions/{session_id}/notes", response_model=list[NoteResponse])
async def get_notes(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: TrainingUseCases = Depends(get_training_use_cases),
):
    return await use_cases.list_notes(session_id, current_user)


@router.post("/sessions/{session_id}/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    session_id: str,
    request: CreateNoteRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: TrainingUseCases = Depends(get_training_use_cases),
):
    note = await use_cases.create_note(session_id, request.model_dump(), current_user)
    logger.info("training_note_created", note_id=note.id, session_id=session_id)
    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: TrainingUseCases = Depends(get_training_use_cases),
):
    try:
        await use_cases.delete_note(note_id, current_user)
    except TrainingNoteNotFoundError:
        raise HTTPException(status_code=404, detail="Note not found")


# ── Missing Element Routes ───────────────────────

@router.get("/sessions/{session_id}/missing", response_model=list[MissingResponse])
async def get_missing(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: TrainingUseCases = Depends(get_training_use_cases),
):
    return await use_cases.list_missing(session_id, current_user)


@router.post("/sessions/{session_id}/missing", response_model=MissingResponse, status_code=status.HTTP_201_CREATED)
async def create_missing(
    session_id: str,
    request: CreateMissingRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: TrainingUseCases = Depends(get_training_use_cases),
):
    item = await use_cases.create_missing(session_id, request.model_dump(), current_user)
    logger.info("training_missing_created", item_id=item.id, label=request.label)
    return item


@router.delete("/missing/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_missing(
    item_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: TrainingUseCases = Depends(get_training_use_cases),
):
    try:
        await use_cases.delete_missing(item_id, current_user)
    except TrainingMissingElementNotFoundError:
        raise HTTPException(status_code=404, detail="Missing element not found")
