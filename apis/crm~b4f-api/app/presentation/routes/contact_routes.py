"""Contact routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.contact_repository import ContactRepository
from app.domain.entities.contact import Contact
from app.presentation.schemas.crm_schemas import ContactCreate, ContactUpdate, ContactResponse, ContactListResponse

router = APIRouter(prefix="/api/v1/contacts")

@router.get("", response_model=ContactListResponse)
async def list_contacts(skip: int = 0, limit: int = 50, search: str = Query(None), organization_id: str = Query(None),
                         user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ContactRepository(db)
    items = repo.list_all(user["tenant_id"], skip, limit, search, organization_id)
    total = repo.count(user["tenant_id"], organization_id)
    return ContactListResponse(items=[ContactResponse.model_validate(c) for c in items], total=total, skip=skip, limit=limit)

@router.post("", response_model=ContactResponse, status_code=201)
async def create_contact(data: ContactCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ContactRepository(db)
    contact = Contact(**data.model_dump(), tenant_id=user["tenant_id"], owner_id=user["user_id"], created_by=user["email"])
    return ContactResponse.model_validate(repo.create(contact))

@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ContactRepository(db)
    contact = repo.get_by_id(contact_id, user["tenant_id"])
    if not contact: raise HTTPException(status_code=404, detail="Contact not found")
    return ContactResponse.model_validate(contact)

@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(contact_id: str, data: ContactUpdate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ContactRepository(db)
    contact = repo.get_by_id(contact_id, user["tenant_id"])
    if not contact: raise HTTPException(status_code=404, detail="Contact not found")
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(contact, k, v)
    contact.updated_by = user["email"]
    return ContactResponse.model_validate(repo.update(contact))

@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: str, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = ContactRepository(db)
    contact = repo.get_by_id(contact_id, user["tenant_id"])
    if not contact: raise HTTPException(status_code=404, detail="Contact not found")
    repo.soft_delete(contact, user["email"])
