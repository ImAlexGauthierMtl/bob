"""Email CRUD routes — pure storage, no business logic."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.use_cases.ms365_core_use_cases import MS365CoreUseCases
from app.domain.exceptions import EmailNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_ms365_core_use_cases
from app.presentation.schemas.ms365_schemas import (
    EmailUpsertRequest,
    EmailUpdateRequest,
    EmailResponse,
    EmailListResponse,
)

router = APIRouter(prefix="/api/v1/emails")


@router.get("", response_model=EmailListResponse)
async def list_emails(
    user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    folder: Optional[str] = None,
    search: Optional[str] = None,
    smart_label: Optional[str] = None,
    linked_contact_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """List synced emails for a user."""
    result = await use_cases.list_emails(
        user_id,
        current_user["tenant_id"],
        skip,
        limit,
        folder,
        search,
        linked_contact_id,
        smart_label,
    )
    return EmailListResponse(
        items=[EmailResponse.model_validate(e) for e in result.items],
        total=result.total, skip=result.skip, limit=result.limit,
    )


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Get a specific synced email."""
    try:
        email = await use_cases.get_email(email_id, user_id, current_user["tenant_id"])
    except EmailNotFoundError:
        raise HTTPException(status_code=404, detail="Email not found")
    return EmailResponse.model_validate(email)


@router.post("", response_model=EmailResponse, status_code=status.HTTP_201_CREATED)
async def upsert_email(
    data: EmailUpsertRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Upsert (insert or update) a synced email."""
    email = await use_cases.upsert_email(data.model_dump(), current_user["tenant_id"])
    return EmailResponse.model_validate(email)


@router.patch("/{email_id}", response_model=EmailResponse)
async def update_email(
    email_id: str,
    data: EmailUpdateRequest,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Update email metadata (labels, read status, CRM linking)."""
    try:
        updated = await use_cases.update_email(
            email_id,
            user_id,
            current_user["tenant_id"],
            data.model_dump(exclude_unset=True),
        )
    except EmailNotFoundError:
        raise HTTPException(status_code=404, detail="Email not found")
    return EmailResponse.model_validate(updated)


@router.delete("/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email(
    email_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Hard-delete a synced email."""
    try:
        await use_cases.delete_email(email_id, user_id, current_user["tenant_id"])
    except EmailNotFoundError:
        raise HTTPException(status_code=404, detail="Email not found")
