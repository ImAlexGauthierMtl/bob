"""Training routes — CRUD for training sessions, notes, and missing elements."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

import structlog

from app.middleware.auth import get_current_user
from app.infrastructure.database import get_session_factory
from app.infrastructure.persistence.models.training_models import (
    TrainingSession,
    TrainingNote,
    TrainingMissingElement,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/training")

SessionLocal = None


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


# ── Helper ───────────────────────────────────────

def get_db():
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Session Routes ───────────────────────────────

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    session = TrainingSession(
        id=str(uuid.uuid4()),
        user_id=current_user["user_id"],
        tenant_id=current_user["tenant_id"],
        training_slug=request.training_slug,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("training_session_created", session_id=session.id, slug=request.training_slug)
    return session


@router.patch("/sessions/{session_id}/slide")
async def update_slide(
    session_id: str,
    request: UpdateSlideRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    session = db.query(TrainingSession).filter(
        TrainingSession.id == session_id,
        TrainingSession.user_id == current_user["user_id"],
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.current_slide = request.current_slide
    db.commit()
    return {"status": "ok", "current_slide": request.current_slide}


# ── Note Routes ──────────────────────────────────

@router.get("/sessions/{session_id}/notes", response_model=list[NoteResponse])
async def get_notes(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    notes = db.query(TrainingNote).filter(
        TrainingNote.session_id == session_id,
        TrainingNote.user_id == current_user["user_id"],
    ).order_by(TrainingNote.created_at.asc()).all()
    return notes


@router.post("/sessions/{session_id}/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    session_id: str,
    request: CreateNoteRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    note = TrainingNote(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user["user_id"],
        slide_id=request.slide_id,
        content=request.content,
        note_type=request.note_type,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    logger.info("training_note_created", note_id=note.id, session_id=session_id)
    return note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    note = db.query(TrainingNote).filter(
        TrainingNote.id == note_id,
        TrainingNote.user_id == current_user["user_id"],
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()


# ── Missing Element Routes ───────────────────────

@router.get("/sessions/{session_id}/missing", response_model=list[MissingResponse])
async def get_missing(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    items = db.query(TrainingMissingElement).filter(
        TrainingMissingElement.session_id == session_id,
        TrainingMissingElement.user_id == current_user["user_id"],
    ).order_by(TrainingMissingElement.created_at.asc()).all()
    return items


@router.post("/sessions/{session_id}/missing", response_model=MissingResponse, status_code=status.HTTP_201_CREATED)
async def create_missing(
    session_id: str,
    request: CreateMissingRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    item = TrainingMissingElement(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user["user_id"],
        label=request.label,
        category=request.category,
        description=request.description,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    logger.info("training_missing_created", item_id=item.id, label=request.label)
    return item


@router.delete("/missing/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_missing(
    item_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    item = db.query(TrainingMissingElement).filter(
        TrainingMissingElement.id == item_id,
        TrainingMissingElement.user_id == current_user["user_id"],
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Missing element not found")
    db.delete(item)
    db.commit()
