"""Email CRUD routes — pure storage, no business logic."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.events.publishers import publish_email_received
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
    db: Session = Depends(get_db),
):
    """List synced emails for a user."""
    repo = MS365Repository(db)
    items = repo.list_emails(user_id, current_user["tenant_id"], skip, limit, folder, search, linked_contact_id, smart_label)
    total = repo.count_emails(user_id, current_user["tenant_id"], folder, search, linked_contact_id, smart_label)
    return EmailListResponse(
        items=[EmailResponse.model_validate(e) for e in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific synced email."""
    repo = MS365Repository(db)
    email = repo.get_email_by_id(email_id, user_id, current_user["tenant_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return EmailResponse.model_validate(email)


@router.post("", response_model=EmailResponse, status_code=status.HTTP_201_CREATED)
async def upsert_email(
    data: EmailUpsertRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upsert (insert or update) a synced email."""
    repo = MS365Repository(db)
    email = repo.upsert_email(data.model_dump(), current_user["tenant_id"])
    await publish_email_received(email.id, {"subject": email.subject, "from": email.from_address})
    return EmailResponse.model_validate(email)


@router.patch("/{email_id}", response_model=EmailResponse)
async def update_email(
    email_id: str,
    data: EmailUpdateRequest,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update email metadata (labels, read status, CRM linking)."""
    repo = MS365Repository(db)
    email = repo.get_email_by_id(email_id, user_id, current_user["tenant_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    updates = data.model_dump(exclude_unset=True)
    updated = repo.update_email(email, updates)
    return EmailResponse.model_validate(updated)


@router.delete("/{email_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email(
    email_id: str,
    user_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hard-delete a synced email."""
    repo = MS365Repository(db)
    email = repo.get_email_by_id(email_id, user_id, current_user["tenant_id"])
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    repo.delete_email(email)
