"""FastAPI routes for Client Map 360° — CRUD + behavioral analysis."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.domain.entities.user import User
from app.domain.entities.contact import Contact
from app.infrastructure.persistence.client_map_repository import ClientMapRepository
from app.presentation.schemas.client_map_schemas import (
    ClientMapUpsert, ClientMapResponse,
    GoldenNoteCreate, GoldenNoteUpdate, GoldenNoteResponse,
    MeddpiccScoreDetail,
)

router = APIRouter(prefix="/api/v1/contacts/{contact_id}/client-map")


def _verify_contact(contact_id: str, user: User, db: Session) -> Contact:
    """Verify contact exists and belongs to user's tenant."""
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.tenant_id == user.tenant_id,
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


# ── Client Map CRUD ──────────────────────────────────────────

@router.get("", response_model=ClientMapResponse)
async def get_client_map(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the Client Map 360° for a contact."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    client_map = repo.get_by_contact_id(contact_id, current_user.tenant_id)
    if not client_map:
        raise HTTPException(status_code=404, detail="Client Map not found for this contact")
    return client_map


@router.put("", response_model=ClientMapResponse)
async def upsert_client_map(
    contact_id: str,
    payload: ClientMapUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update the Client Map for a contact."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    data = payload.model_dump(exclude_unset=True)
    client_map = repo.upsert(
        contact_id=contact_id,
        tenant_id=current_user.tenant_id,
        data=data,
        user_email=current_user.email or "",
    )
    return client_map


# ── Golden Notes ─────────────────────────────────────────────

@router.post("/golden-notes", response_model=GoldenNoteResponse, status_code=201)
async def create_golden_note(
    contact_id: str,
    payload: GoldenNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a Golden Note to the contact's Client Map."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)

    # Ensure client map exists (auto-create if needed)
    client_map = repo.get_by_contact_id(contact_id, current_user.tenant_id)
    if not client_map:
        client_map = repo.upsert(
            contact_id=contact_id,
            tenant_id=current_user.tenant_id,
            data={},
            user_email=current_user.email or "",
        )

    note = repo.add_golden_note(
        client_map_id=client_map.id,
        tenant_id=current_user.tenant_id,
        data=payload.model_dump(),
        user_email=current_user.email or "",
    )
    return note


@router.put("/golden-notes/{note_id}", response_model=GoldenNoteResponse)
async def update_golden_note(
    contact_id: str,
    note_id: str,
    payload: GoldenNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing Golden Note."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    data = payload.model_dump(exclude_unset=True)
    note = repo.update_golden_note(note_id, current_user.tenant_id, data)
    if not note:
        raise HTTPException(status_code=404, detail="Golden Note not found")
    return note


@router.delete("/golden-notes/{note_id}", status_code=204)
async def delete_golden_note(
    contact_id: str,
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a Golden Note (soft-delete)."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    success = repo.delete_golden_note(note_id, current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Golden Note not found")


# ── MEDDPICC Score ───────────────────────────────────────────

@router.get("/meddpicc-score", response_model=MeddpiccScoreDetail)
async def get_meddpicc_score(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed MEDDPICC score breakdown."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)
    detail = repo.get_meddpicc_detail(contact_id, current_user.tenant_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Client Map not found for this contact")
    return detail


# ── Behavioral Analysis ─────────────────────────────────────

@router.post("/analyze-behavior")
async def trigger_behavioral_analysis(
    contact_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger AI behavioral analysis from interaction data."""
    _verify_contact(contact_id, current_user, db)
    repo = ClientMapRepository(db)

    # Ensure client map exists
    client_map = repo.get_by_contact_id(contact_id, current_user.tenant_id)
    if not client_map:
        client_map = repo.upsert(
            contact_id=contact_id,
            tenant_id=current_user.tenant_id,
            data={},
            user_email=current_user.email or "",
        )

    try:
        from app.application.use_cases.behavioral_analyzer import BehavioralAnalyzer
        analyzer = BehavioralAnalyzer(db)
        profile = await analyzer.analyze(
            contact_id=contact_id,
            tenant_id=current_user.tenant_id,
            client_map=client_map,
        )
        return {"status": "ok", "behavioral_profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
