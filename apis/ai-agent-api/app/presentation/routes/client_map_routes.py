"""FastAPI routes for Client Map 360° — CRUD + behavioral analysis.

Cross-service note: Contact entity lives in CRM API, but we share the
same database, so we query the 'contacts' table directly via text SQL.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.client_map_repository import ClientMapRepository
from app.presentation.schemas.client_map_schemas import (
    ClientMapUpsert, ClientMapResponse,
    GoldenNoteCreate, GoldenNoteUpdate, GoldenNoteResponse,
    MeddpiccScoreDetail,
)

router = APIRouter(prefix="/api/v1/contacts/{contact_id}/client-map")


def _verify_contact(contact_id: str, user: dict, db: Session):
    """Verify contact exists and belongs to user's tenant (cross-service query)."""
    result = db.execute(
        text("SELECT id FROM contacts WHERE id = :id AND tenant_id = :tid AND deleted_at IS NULL"),
        {"id": contact_id, "tid": user["tenant_id"]},
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")


# ── Client Map CRUD ──────────────────────────────────────────

@router.get("", response_model=ClientMapResponse)
async def get_client_map(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get the Client Map 360° for a contact."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    client_map = repo.get_by_contact_id(contact_id, current_user["tenant_id"])
    if not client_map:
        raise HTTPException(status_code=404, detail="Client Map not found for this contact")
    return client_map


@router.put("", response_model=ClientMapResponse)
async def upsert_client_map(
    contact_id: str,
    payload: ClientMapUpsert,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create or update the Client Map for a contact."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    data = payload.model_dump(exclude_unset=True)
    client_map = repo.upsert(
        contact_id=contact_id,
        tenant_id=current_user["tenant_id"],
        data=data,
        user_email=current_user["email"] or "",
    )
    return client_map


# ── Golden Notes ─────────────────────────────────────────────

@router.post("/golden-notes", response_model=GoldenNoteResponse, status_code=201)
async def create_golden_note(
    contact_id: str,
    payload: GoldenNoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Add a Golden Note to the contact's Client Map."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    client_map = repo.get_by_contact_id(contact_id, current_user["tenant_id"])
    if not client_map:
        client_map = repo.upsert(
            contact_id=contact_id, tenant_id=current_user["tenant_id"],
            data={}, user_email=current_user["email"] or "",
        )
    note = repo.add_golden_note(
        client_map_id=client_map.id, tenant_id=current_user["tenant_id"],
        data=payload.model_dump(), user_email=current_user["email"] or "",
    )
    return note


@router.put("/golden-notes/{note_id}", response_model=GoldenNoteResponse)
async def update_golden_note(
    contact_id: str, note_id: str, payload: GoldenNoteUpdate,
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),
):
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    note = repo.update_golden_note(note_id, current_user["tenant_id"], payload.model_dump(exclude_unset=True))
    if not note:
        raise HTTPException(status_code=404, detail="Golden Note not found")
    return note


@router.delete("/golden-notes/{note_id}", status_code=204)
async def delete_golden_note(
    contact_id: str, note_id: str,
    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),
):
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    if not repo.delete_golden_note(note_id, current_user["tenant_id"]):
        raise HTTPException(status_code=404, detail="Golden Note not found")


# ── MEDDPICC Score ───────────────────────────────────────────

@router.get("/meddpicc-score", response_model=MeddpiccScoreDetail)
async def get_meddpicc_score(
    contact_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),
):
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    detail = repo.get_meddpicc_detail(contact_id, current_user["tenant_id"])
    if not detail:
        raise HTTPException(status_code=404, detail="Client Map not found for this contact")
    return detail


# ── Behavioral Analysis ─────────────────────────────────────

@router.post("/analyze-behavior")
async def trigger_behavioral_analysis(
    contact_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user),
):
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    client_map = repo.get_by_contact_id(contact_id, current_user["tenant_id"])
    if not client_map:
        client_map = repo.upsert(
            contact_id=contact_id, tenant_id=current_user["tenant_id"],
            data={}, user_email=current_user["email"] or "",
        )
    try:
        from app.application.use_cases.behavioral_analyzer import BehavioralAnalyzer
        analyzer = BehavioralAnalyzer(db)
        profile = await analyzer.analyze(
            contact_id=contact_id, tenant_id=current_user["tenant_id"], client_map=client_map,
        )
        return {"status": "ok", "behavioral_profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
