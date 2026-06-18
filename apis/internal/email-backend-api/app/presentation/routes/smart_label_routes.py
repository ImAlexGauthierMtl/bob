"""Smart Label CRUD routes — pure storage, no business logic."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.smart_label_repository import SmartLabelRepository
from app.infrastructure.persistence.models.smart_label import SmartLabel
from app.presentation.schemas.smart_label_schemas import (
    SmartLabelCreate,
    SmartLabelUpdate,
    SmartLabelResponse,
    SmartLabelListResponse,
)

router = APIRouter(prefix="/api/v1/smart-labels")


@router.post("", response_model=SmartLabelResponse, status_code=status.HTTP_201_CREATED)
async def create_smart_label(
    data: SmartLabelCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new smart label."""
    repo = SmartLabelRepository(db)
    existing = repo.get_by_name(data.name, current_user["tenant_id"], data.parent_id)
    if existing:
        raise HTTPException(status_code=400, detail="A label with this name already exists in this context")
    label = SmartLabel(
        name=data.name.strip(),
        color=data.color.strip(),
        description=data.description,
        keywords=data.keywords or [],
        prompt_hint=data.prompt_hint,
        parent_id=data.parent_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
    )
    return repo.create(label)


@router.get("", response_model=SmartLabelListResponse)
async def list_smart_labels(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all smart labels."""
    repo = SmartLabelRepository(db)
    items = repo.list_all(current_user["tenant_id"], skip, limit)
    total = repo.count(current_user["tenant_id"])
    return SmartLabelListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{label_id}", response_model=SmartLabelResponse)
async def get_smart_label(
    label_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a smart label by ID."""
    repo = SmartLabelRepository(db)
    label = repo.get_by_id(label_id, current_user["tenant_id"])
    if not label:
        raise HTTPException(status_code=404, detail="Smart label not found")
    return label


@router.patch("/{label_id}", response_model=SmartLabelResponse)
async def update_smart_label(
    label_id: str,
    data: SmartLabelUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a smart label."""
    repo = SmartLabelRepository(db)
    label = repo.get_by_id(label_id, current_user["tenant_id"])
    if not label:
        raise HTTPException(status_code=404, detail="Smart label not found")
    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data:
        new_parent_id = update_data.get("parent_id", label.parent_id)
        existing = repo.get_by_name(update_data["name"], current_user["tenant_id"], new_parent_id)
        if existing and existing.id != label_id:
            raise HTTPException(status_code=400, detail="A label with this name already exists in this context")
    for key, value in update_data.items():
        setattr(label, key, value)
    label.updated_by = current_user["email"]
    return repo.update(label)


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_smart_label(
    label_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a smart label."""
    repo = SmartLabelRepository(db)
    label = repo.get_by_id(label_id, current_user["tenant_id"])
    if not label:
        raise HTTPException(status_code=404, detail="Smart label not found")
    try:
        repo.delete(label)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
