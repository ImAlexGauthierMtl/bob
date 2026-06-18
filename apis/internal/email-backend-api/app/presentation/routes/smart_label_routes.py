"""Smart Label CRUD routes — pure storage, no business logic."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.application.use_cases.smart_label_use_cases import SmartLabelUseCases
from app.domain.exceptions import SmartLabelDeleteError, SmartLabelDuplicateError, SmartLabelNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_smart_label_use_cases
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
    use_cases: SmartLabelUseCases = Depends(get_smart_label_use_cases),
):
    """Create a new smart label."""
    try:
        return await use_cases.create_smart_label(data.model_dump(), current_user)
    except SmartLabelDuplicateError:
        raise HTTPException(status_code=400, detail="A label with this name already exists in this context")


@router.get("", response_model=SmartLabelListResponse)
async def list_smart_labels(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    use_cases: SmartLabelUseCases = Depends(get_smart_label_use_cases),
):
    """List all smart labels."""
    result = await use_cases.list_smart_labels(current_user["tenant_id"], skip, limit)
    return SmartLabelListResponse(items=result.items, total=result.total, skip=result.skip, limit=result.limit)


@router.get("/{label_id}", response_model=SmartLabelResponse)
async def get_smart_label(
    label_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: SmartLabelUseCases = Depends(get_smart_label_use_cases),
):
    """Get a smart label by ID."""
    try:
        return await use_cases.get_smart_label(label_id, current_user["tenant_id"])
    except SmartLabelNotFoundError:
        raise HTTPException(status_code=404, detail="Smart label not found")


@router.patch("/{label_id}", response_model=SmartLabelResponse)
async def update_smart_label(
    label_id: str,
    data: SmartLabelUpdate,
    current_user: dict = Depends(get_current_user),
    use_cases: SmartLabelUseCases = Depends(get_smart_label_use_cases),
):
    """Update a smart label."""
    try:
        return await use_cases.update_smart_label(label_id, data.model_dump(exclude_unset=True), current_user)
    except SmartLabelNotFoundError:
        raise HTTPException(status_code=404, detail="Smart label not found")
    except SmartLabelDuplicateError:
        raise HTTPException(status_code=400, detail="A label with this name already exists in this context")


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_smart_label(
    label_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: SmartLabelUseCases = Depends(get_smart_label_use_cases),
):
    """Delete a smart label."""
    try:
        await use_cases.delete_smart_label(label_id, current_user["tenant_id"])
    except SmartLabelNotFoundError:
        raise HTTPException(status_code=404, detail="Smart label not found")
    except SmartLabelDeleteError as e:
        raise HTTPException(status_code=400, detail=str(e))
