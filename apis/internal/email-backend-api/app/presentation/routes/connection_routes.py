"""Connection CRUD routes — pure storage, no business logic."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.presentation.schemas.ms365_schemas import (
    ConnectionCreateRequest,
    ConnectionUpdateRequest,
    ConnectionResponse,
    ConnectionDetailResponse,
)

router = APIRouter(prefix="/api/v1/connections")


@router.get("/by-user/{user_id}", response_model=Optional[ConnectionDetailResponse])
async def get_connection_by_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get connection by user ID (returns full detail including tokens)."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_user(user_id, current_user["tenant_id"])
    if not conn:
        return None
    return ConnectionDetailResponse.model_validate(conn)


@router.get("/{conn_id}", response_model=ConnectionDetailResponse)
async def get_connection(
    conn_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get connection by ID."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_id(conn_id, current_user["tenant_id"])
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return ConnectionDetailResponse.model_validate(conn)


@router.get("/active/all")
async def list_active_connections(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active connections (for background sync tasks)."""
    repo = MS365Repository(db)
    conns = repo.get_all_active_connections()
    return [ConnectionResponse.model_validate(c) for c in conns]


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    data: ConnectionCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new MS365 connection."""
    repo = MS365Repository(db)
    existing = repo.get_connection_by_user(data.user_id, current_user["tenant_id"])
    if existing:
        raise HTTPException(status_code=409, detail="User already has a connection")
    conn = repo.create_connection(data.model_dump(), current_user["tenant_id"])
    return ConnectionResponse.model_validate(conn)


@router.patch("/{conn_id}", response_model=ConnectionDetailResponse)
async def update_connection(
    conn_id: str,
    data: ConnectionUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a connection."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_id(conn_id, current_user["tenant_id"])
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    updates = data.model_dump(exclude_unset=True)
    updated = repo.update_connection(conn, updates)
    return ConnectionDetailResponse.model_validate(updated)


@router.delete("/{conn_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    conn_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft-delete a connection."""
    repo = MS365Repository(db)
    conn = repo.get_connection_by_id(conn_id, current_user["tenant_id"])
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    repo.soft_delete_connection(conn, current_user.get("email", "system"))
