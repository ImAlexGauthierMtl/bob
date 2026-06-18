"""Membrane routes — CRUD for Membrane-backed connections, emails, events.

These endpoints are called by the communication-b4f-api webhook handlers
and by the frontend when displaying Membrane Outlook data in /settings/ms365.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.use_cases.membrane_crud_use_cases import MembraneCrudUseCases
from app.domain.exceptions import ConnectionNotFoundError, EmailNotFoundError, EventNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_membrane_crud_use_cases
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
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    """Create a Membrane connection record (usually called by webhook or B4F after connect)."""
    conn = await use_cases.create_connection(data.model_dump(exclude_unset=True), current_user["tenant_id"])
    return MembraneConnectionResponse.model_validate(conn)


@router.get("/connections/by-user/{user_id}", response_model=MembraneConnectionResponse)
async def get_connection_by_user(
    user_id: str,
    integration_key: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    """Get a user's Membrane connection (optionally filtered by integration_key)."""
    try:
        conn = await use_cases.get_connection_by_user(user_id, integration_key, current_user["tenant_id"])
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")
    return MembraneConnectionResponse.model_validate(conn)


@router.get("/connections/{connection_id}", response_model=MembraneConnectionResponse)
async def get_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    try:
        conn = await use_cases.get_connection(connection_id, current_user["tenant_id"])
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")
    return MembraneConnectionResponse.model_validate(conn)


@router.patch("/connections/{connection_id}", response_model=MembraneConnectionResponse)
async def update_connection(
    connection_id: str,
    data: MembraneConnectionCreateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    try:
        updated = await use_cases.update_connection(
            connection_id,
            data.model_dump(exclude_unset=True),
            current_user["tenant_id"],
        )
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")
    return MembraneConnectionResponse.model_validate(updated)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    try:
        await use_cases.delete_connection(connection_id, current_user)
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")


# ── Email CRUD ───────────────────────────────────────────────────

@router.post("/emails", response_model=MembraneEmailResponse, status_code=status.HTTP_201_CREATED)
async def upsert_email(
    data: MembraneEmailUpsertRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    """Upsert an email ingested via Membrane webhook."""
    email = await use_cases.upsert_email(data.model_dump(), current_user["tenant_id"])
    return MembraneEmailResponse.model_validate(email)


@router.get("/emails", response_model=MembraneEmailListResponse)
async def list_emails(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    folder: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    """List Membrane-synced emails for a user."""
    result = await use_cases.list_emails(user_id, current_user["tenant_id"], skip, limit, folder, search)
    return MembraneEmailListResponse(
        items=[MembraneEmailResponse.model_validate(e) for e in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
    )


@router.get("/emails/{email_id}", response_model=MembraneEmailResponse)
async def get_email(
    email_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    try:
        email = await use_cases.get_email(email_id, user_id, current_user["tenant_id"])
    except EmailNotFoundError:
        raise HTTPException(status_code=404, detail="Email not found")
    return MembraneEmailResponse.model_validate(email)


# ── Event CRUD ───────────────────────────────────────────────────

@router.post("/events", response_model=MembraneEventResponse, status_code=status.HTTP_201_CREATED)
async def upsert_event(
    data: MembraneEventUpsertRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    """Upsert an event ingested via Membrane webhook."""
    event = await use_cases.upsert_event(data.model_dump(), current_user["tenant_id"])
    return MembraneEventResponse.model_validate(event)


@router.get("/events", response_model=MembraneEventListResponse)
async def list_events(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    """List Membrane-synced events for a user."""
    result = await use_cases.list_events(user_id, current_user["tenant_id"], skip, limit, from_date, to_date)
    return MembraneEventListResponse(
        items=[MembraneEventResponse.model_validate(e) for e in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
    )


@router.get("/events/{event_id}", response_model=MembraneEventResponse)
async def get_event(
    event_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    use_cases: MembraneCrudUseCases = Depends(get_membrane_crud_use_cases),
):
    try:
        event = await use_cases.get_event(event_id, user_id, current_user["tenant_id"])
    except EventNotFoundError:
        raise HTTPException(status_code=404, detail="Event not found")
    return MembraneEventResponse.model_validate(event)
