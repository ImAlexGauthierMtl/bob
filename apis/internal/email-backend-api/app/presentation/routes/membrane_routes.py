"""Membrane routes — CRUD for Membrane-backed connections, emails, events.

These endpoints are called by the communication-b4f-api webhook handlers
and by the frontend when displaying Membrane Outlook data in /settings/ms365.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.membrane_repository import MembraneRepository
from app.presentation.schemas.membrane_schemas import (
    MembraneConnectionCreateRequest,
    MembraneConnectionResponse,
    MembraneEmailUpsertRequest,
    MembraneEmailResponse,
    MembraneEmailListResponse,
    MembraneEventUpsertRequest,
    MembraneEventResponse,
    MembraneEventListResponse,
)

router = APIRouter(prefix="/api/v1/membrane")


# ── Connection CRUD ──────────────────────────────────────────────

@router.post("/connections", response_model=MembraneConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    data: MembraneConnectionCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Membrane connection record (usually called by webhook or B4F after connect)."""
    repo = MembraneRepository(db)
    existing = repo.get_connection_by_user_integration(
        data.user_id, data.integration_key, current_user["tenant_id"]
    )
    if existing:
        updated = repo.update_connection(existing, data.model_dump(exclude_unset=True))
        return MembraneConnectionResponse.model_validate(updated)
    conn = repo.create_connection(data.model_dump(), current_user["tenant_id"])
    return MembraneConnectionResponse.model_validate(conn)


@router.get("/connections/by-user/{user_id}", response_model=MembraneConnectionResponse)
async def get_connection_by_user(
    user_id: str,
    integration_key: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a user's Membrane connection (optionally filtered by integration_key)."""
    repo = MembraneRepository(db)
    if integration_key:
        conn = repo.get_connection_by_user_integration(user_id, integration_key, current_user["tenant_id"])
    else:
        # Return first active connection (simplification for single-integration users)
        from app.infrastructure.persistence.models.membrane_connection import MembraneConnection as MC
        conn = db.query(MC).filter(
            MC.user_id == user_id, MC.tenant_id == current_user["tenant_id"],
            MC.is_deleted == False,
        ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return MembraneConnectionResponse.model_validate(conn)


@router.get("/connections/{connection_id}", response_model=MembraneConnectionResponse)
async def get_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = MembraneRepository(db)
    from app.infrastructure.persistence.models.membrane_connection import MembraneConnection as MC
    conn = db.query(MC).filter(
        MC.id == connection_id, MC.tenant_id == current_user["tenant_id"], MC.is_deleted == False,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return MembraneConnectionResponse.model_validate(conn)


@router.patch("/connections/{connection_id}", response_model=MembraneConnectionResponse)
async def update_connection(
    connection_id: str,
    data: MembraneConnectionCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = MembraneRepository(db)
    from app.infrastructure.persistence.models.membrane_connection import MembraneConnection as MC
    conn = db.query(MC).filter(
        MC.id == connection_id, MC.tenant_id == current_user["tenant_id"], MC.is_deleted == False,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    updated = repo.update_connection(conn, data.model_dump(exclude_unset=True))
    return MembraneConnectionResponse.model_validate(updated)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = MembraneRepository(db)
    from app.infrastructure.persistence.models.membrane_connection import MembraneConnection as MC
    conn = db.query(MC).filter(
        MC.id == connection_id, MC.tenant_id == current_user["tenant_id"], MC.is_deleted == False,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    repo.soft_delete_connection(conn, current_user.get("user_id", "system"))


# ── Email CRUD ───────────────────────────────────────────────────

@router.post("/emails", response_model=MembraneEmailResponse, status_code=status.HTTP_201_CREATED)
async def upsert_email(
    data: MembraneEmailUpsertRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upsert an email ingested via Membrane webhook."""
    repo = MembraneRepository(db)
    email = repo.upsert_email(data.model_dump(), current_user["tenant_id"])
    return MembraneEmailResponse.model_validate(email)


@router.get("/emails", response_model=MembraneEmailListResponse)
async def list_emails(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    folder: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List Membrane-synced emails for a user."""
    repo = MembraneRepository(db)
    items = repo.list_emails(user_id, current_user["tenant_id"], skip, limit, folder, search)
    total = repo.count_emails(user_id, current_user["tenant_id"], folder, search)
    return MembraneEmailListResponse(
        items=[MembraneEmailResponse.model_validate(e) for e in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/emails/{email_id}", response_model=MembraneEmailResponse)
async def get_email(
    email_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = MembraneRepository(db)
    email = repo.get_email_by_id(email_id, user_id, current_user["tenant_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return MembraneEmailResponse.model_validate(email)


# ── Event CRUD ───────────────────────────────────────────────────

@router.post("/events", response_model=MembraneEventResponse, status_code=status.HTTP_201_CREATED)
async def upsert_event(
    data: MembraneEventUpsertRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upsert an event ingested via Membrane webhook."""
    repo = MembraneRepository(db)
    event = repo.upsert_event(data.model_dump(), current_user["tenant_id"])
    return MembraneEventResponse.model_validate(event)


@router.get("/events", response_model=MembraneEventListResponse)
async def list_events(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List Membrane-synced events for a user."""
    repo = MembraneRepository(db)
    items = repo.list_events(user_id, current_user["tenant_id"], skip, limit, from_date, to_date)
    total = repo.count_events(user_id, current_user["tenant_id"], from_date, to_date)
    return MembraneEventListResponse(
        items=[MembraneEventResponse.model_validate(e) for e in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/events/{event_id}", response_model=MembraneEventResponse)
async def get_event(
    event_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = MembraneRepository(db)
    event = repo.get_event_by_id(event_id, user_id, current_user["tenant_id"])
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return MembraneEventResponse.model_validate(event)
