"""Contact routes — CRUD API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.middleware.authorization import require_permission
from app.domain.entities.contact import Contact
from app.agents.event_bus import event_bus
from app.infrastructure.persistence.contact_repository import ContactRepository
from app.presentation.schemas.contact_schemas import (
    ContactCreate, ContactUpdate, ContactResponse, ContactListResponse,
)

router = APIRouter(prefix="/api/v1/contacts")


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    organization_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ContactRepository(db)
    items = repo.list_all(current_user["tenant_id"], skip, limit, search, organization_id)
    total = repo.count(current_user["tenant_id"], organization_id)
    return ContactListResponse(
        items=[ContactResponse.model_validate(c) for c in items],
        total=total, skip=skip, limit=limit,
    )


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_permission("contact:write"))])
async def create_contact(
    data: ContactCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ContactRepository(db)
    contact = Contact(**data.model_dump(exclude_none=True), tenant_id=current_user["tenant_id"], created_by=current_user["email"])
    created = repo.create(contact)
    # Fire event for workflow triggers
    import asyncio
    asyncio.ensure_future(event_bus.publish(
        "contact.created", {"contact_id": created.id}, db, current_user["tenant_id"], current_user["email"]
    ))
    return ContactResponse.model_validate(created)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ContactRepository(db)
    contact = repo.get_by_id(contact_id, current_user["tenant_id"])
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return ContactResponse.model_validate(contact)


@router.patch("/{con_id}", response_model=ContactResponse,
              dependencies=[Depends(require_permission("contact:write"))])
async def update_contact(
    contact_id: str,
    data: ContactUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ContactRepository(db)
    contact = repo.get_by_id(contact_id, current_user["tenant_id"])
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(contact, k, v)
    contact.updated_by = current_user["email"]
    return ContactResponse.model_validate(repo.update(contact))


@router.delete("/{con_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_permission("contact:delete"))])
async def delete_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    repo = ContactRepository(db)
    contact = repo.get_by_id(contact_id, current_user["tenant_id"])
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    repo.soft_delete(contact, current_user["email"])
    # Fire event for workflow triggers
    import asyncio
    asyncio.ensure_future(event_bus.publish(
        "contact.deleted", {"contact_id": contact_id}, db, current_user["tenant_id"], current_user["email"]
    ))
