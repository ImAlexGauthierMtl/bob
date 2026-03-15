"""Quote CRUD routes — pure storage, no business logic."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.quote_repository import QuoteRepository
from app.domain.entities.quote import Quote
from app.presentation.schemas.quote_schemas import (
    QuoteCreate, QuoteUpdate, QuoteResponse, QuoteListResponse,
)

router = APIRouter(prefix="/api/v1/quotes")


@router.get("", response_model=QuoteListResponse)
async def list_quotes(
    skip: int = 0, limit: int = 50, opportunity_id: str = Query(None),
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, opportunity_id)
    total = repo.count(user["tenant_id"])
    return QuoteListResponse(
        items=[QuoteResponse.model_validate(q) for q in items],
        total=total, skip=skip, limit=limit,
    )


@router.post("", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    data: QuoteCreate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    quote = Quote(
        **data.model_dump(),
        tenant_id=user["tenant_id"],
        owner_id=user["user_id"],
        created_by=user["email"],
    )
    return QuoteResponse.model_validate(repo.create(quote))


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    quote = repo.get_by_id(quote_id, user["tenant_id"])
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteResponse.model_validate(quote)


@router.patch("/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: str, data: QuoteUpdate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    quote = repo.get_by_id(quote_id, user["tenant_id"])
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(quote, k, v)
    quote.updated_by = user["email"]
    return QuoteResponse.model_validate(repo.update(quote))


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = QuoteRepository(db)
    quote = repo.get_by_id(quote_id, user["tenant_id"])
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    repo.soft_delete(quote, user["email"])
