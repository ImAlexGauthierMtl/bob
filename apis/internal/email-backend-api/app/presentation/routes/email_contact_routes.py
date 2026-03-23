"""Email ↔ Contact link CRUD routes — pure storage."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.ms365_repository import MS365Repository
from app.presentation.schemas.ms365_schemas import (
    EmailContactLinkRequest,
    EmailContactLinkResponse,
)

router = APIRouter(prefix="/api/v1/emails/{email_id}/contacts")


@router.get("")
async def list_email_contacts(
    email_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List contacts linked to an email."""
    repo = MS365Repository(db)
    links = repo.get_email_contacts(email_id)
    return [
        EmailContactLinkResponse(
            id=str(row.id), synced_email_id=str(row.synced_email_id),
            contact_id=str(row.contact_id), role=row.role,
        )
        for row in links
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def link_email_contact(
    email_id: str,
    data: EmailContactLinkRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link a contact to an email."""
    repo = MS365Repository(db)
    repo.link_email_contact(email_id, data.contact_id, data.role)
    return {"status": "linked"}


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_email_contact(
    email_id: str,
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink a contact from an email."""
    repo = MS365Repository(db)
    repo.unlink_email_contact(email_id, contact_id)
