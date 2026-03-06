"""Quote routes — CRUD API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.domain.entities.quote import Quote
from app.infrastructure.persistence.quote_repository import QuoteRepository
from app.presentation.schemas.quote_schemas import (
    QuoteCreate, QuoteUpdate, QuoteResponse, QuoteListResponse,
)

router = APIRouter(prefix="/api/v1/quotes")


@router.get("", response_model=QuoteListResponse)
async def list_quotes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    opportunity_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    items = repo.list_all(current_user["tenant_id"], skip, limit, opportunity_id, organization_id)
    total = repo.count(current_user["tenant_id"])
    return QuoteListResponse(
        items=[QuoteResponse.model_validate(q) for q in items],
        total=total, skip=skip, limit=limit,
    )


@router.post("", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    data: QuoteCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    quote = Quote(**data.model_dump(exclude_none=True), tenant_id=current_user["tenant_id"], created_by=current_user["email"])
    created = repo.create(quote)
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "quote.created", {"quote_id": created.id}, db, current_user["tenant_id"], current_user["email"]
    ))
    return QuoteResponse.model_validate(created)


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    quote = repo.get_by_id(quote_id, current_user["tenant_id"])
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    return QuoteResponse.model_validate(quote)


@router.patch("/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: str,
    data: QuoteUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    quote = repo.get_by_id(quote_id, current_user["tenant_id"])
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(quote, k, v)
    quote.updated_by = current_user["email"]
    updated = repo.update(quote)
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "quote.updated", {"quote_id": quote_id}, db, current_user["tenant_id"], current_user["email"]
    ))
    return QuoteResponse.model_validate(updated)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    quote = repo.get_by_id(quote_id, current_user["tenant_id"])
    if not quote:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
    repo.soft_delete(quote, current_user["email"])
    import asyncio
    from app.agents.event_bus import event_bus
    asyncio.ensure_future(event_bus.publish(
        "quote.deleted", {"quote_id": quote_id}, db, current_user["tenant_id"], current_user["email"]
    ))
