"""Quote HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.use_cases.quote_use_cases import QuoteUseCases
from app.domain.exceptions import QuoteNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_quote_use_cases
from app.presentation.schemas.quote_schemas import (
    QuoteCreate, QuoteUpdate, QuoteResponse, QuoteListResponse,
)

router = APIRouter(prefix="/api/v1/quotes")


@router.get("", response_model=QuoteListResponse)
async def list_quotes(
    skip: int = 0, limit: int = 50, opportunity_id: str = Query(None),
    user: dict = Depends(get_current_user),
    use_cases: QuoteUseCases = Depends(get_quote_use_cases),
):
    result = await use_cases.list_quotes(user["tenant_id"], skip, limit, opportunity_id)
    return QuoteListResponse(
        items=[QuoteResponse.model_validate(quote) for quote in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post("", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    data: QuoteCreate,
    user: dict = Depends(get_current_user),
    use_cases: QuoteUseCases = Depends(get_quote_use_cases),
):
    created = await use_cases.create_quote(data.model_dump(), user)
    return QuoteResponse.model_validate(created)


@router.get("/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: str,
    user: dict = Depends(get_current_user),
    use_cases: QuoteUseCases = Depends(get_quote_use_cases),
):
    try:
        quote = await use_cases.get_quote(quote_id, user["tenant_id"])
    except QuoteNotFoundError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteResponse.model_validate(quote)


@router.patch("/{quote_id}", response_model=QuoteResponse)
async def update_quote(
    quote_id: str, data: QuoteUpdate,
    user: dict = Depends(get_current_user),
    use_cases: QuoteUseCases = Depends(get_quote_use_cases),
):
    try:
        updated = await use_cases.update_quote(
            quote_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except QuoteNotFoundError:
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteResponse.model_validate(updated)


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: str,
    user: dict = Depends(get_current_user),
    use_cases: QuoteUseCases = Depends(get_quote_use_cases),
):
    try:
        await use_cases.delete_quote(quote_id, user)
    except QuoteNotFoundError:
        raise HTTPException(status_code=404, detail="Quote not found")
