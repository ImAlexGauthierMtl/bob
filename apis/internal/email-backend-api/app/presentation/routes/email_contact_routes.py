"""Email ↔ Contact link CRUD routes — pure storage."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.use_cases.ms365_core_use_cases import MS365CoreUseCases
from app.middleware.auth import get_current_user
from app.presentation.deps import get_ms365_core_use_cases
from app.presentation.schemas.ms365_schemas import (
    EmailContactLinkRequest,
    EmailContactLinkResponse,
)

router = APIRouter(prefix="/api/v1/emails/{email_id}/contacts")


@router.get("")
async def list_email_contacts(
    email_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """List contacts linked to an email."""
    links = await use_cases.list_email_contacts(email_id)
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
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Link a contact to an email."""
    return await use_cases.link_email_contact(email_id, data.contact_id, data.role)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_email_contact(
    email_id: str,
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: MS365CoreUseCases = Depends(get_ms365_core_use_cases),
):
    """Unlink a contact from an email."""
    await use_cases.unlink_email_contact(email_id, contact_id)
