"""Contact HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.use_cases.contact_use_cases import ContactUseCases
from app.domain.exceptions import ContactNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_contact_use_cases
from app.presentation.schemas.contact_schemas import (
    ContactCreate, ContactUpdate, ContactResponse, ContactListResponse,
)

router = APIRouter(prefix="/api/v1/contacts")


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    skip: int = 0, limit: int = 50,
    search: str = Query(None), organization_id: str = Query(None),
    user: dict = Depends(get_current_user),
    use_cases: ContactUseCases = Depends(get_contact_use_cases),
):
    result = await use_cases.list_contacts(
        user["tenant_id"],
        skip,
        limit,
        search,
        organization_id,
    )
    return ContactListResponse(
        items=[ContactResponse.model_validate(contact) for contact in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    data: ContactCreate,
    user: dict = Depends(get_current_user),
    use_cases: ContactUseCases = Depends(get_contact_use_cases),
):
    created = await use_cases.create_contact(data.model_dump(), user)
    return ContactResponse.model_validate(created)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    user: dict = Depends(get_current_user),
    use_cases: ContactUseCases = Depends(get_contact_use_cases),
):
    try:
        contact = await use_cases.get_contact(contact_id, user["tenant_id"])
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactResponse.model_validate(contact)


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str, data: ContactUpdate,
    user: dict = Depends(get_current_user),
    use_cases: ContactUseCases = Depends(get_contact_use_cases),
):
    try:
        updated = await use_cases.update_contact(
            contact_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactResponse.model_validate(updated)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: str,
    user: dict = Depends(get_current_user),
    use_cases: ContactUseCases = Depends(get_contact_use_cases),
):
    try:
        await use_cases.delete_contact(contact_id, user)
    except ContactNotFoundError:
        raise HTTPException(status_code=404, detail="Contact not found")
