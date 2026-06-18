"""Connection CRUD routes — pure storage, no business logic."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.use_cases.ms365_core_use_cases import MS365CoreUseCases
from app.domain.exceptions import ConnectionAlreadyExistsError, ConnectionNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_ms365_core_use_cases
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
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Get connection by user ID (returns full detail including tokens)."""
    conn = await use_cases.get_connection_by_user(user_id, current_user["tenant_id"])
    if not conn:
        return None
    return ConnectionDetailResponse.model_validate(conn)


@router.get("/{conn_id}", response_model=ConnectionDetailResponse)
async def get_connection(
    conn_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Get connection by ID."""
    try:
        conn = await use_cases.get_connection(conn_id, current_user["tenant_id"])
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")
    return ConnectionDetailResponse.model_validate(conn)


@router.get("/active/all")
async def list_active_connections(
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """List all active connections (for background sync tasks)."""
    conns = await use_cases.list_active_connections()
    return [ConnectionResponse.model_validate(c) for c in conns]


@router.post("", response_model=ConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_connection(
    data: ConnectionCreateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Create a new MS365 connection."""
    try:
        conn = await use_cases.create_connection(data.model_dump(), current_user["tenant_id"])
    except ConnectionAlreadyExistsError:
        raise HTTPException(status_code=409, detail="User already has a connection")
    return ConnectionResponse.model_validate(conn)


@router.patch("/{conn_id}", response_model=ConnectionDetailResponse)
async def update_connection(
    conn_id: str,
    data: ConnectionUpdateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Update a connection."""
    try:
        updated = await use_cases.update_connection(
            conn_id,
            data.model_dump(exclude_unset=True),
            current_user["tenant_id"],
        )
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")
    return ConnectionDetailResponse.model_validate(updated)


@router.delete("/{conn_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    conn_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Soft-delete a connection."""
    try:
        await use_cases.delete_connection(conn_id, current_user)
    except ConnectionNotFoundError:
        raise HTTPException(status_code=404, detail="Connection not found")
