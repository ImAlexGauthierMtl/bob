"""Smart Label routes — proxies CRUD to email~backend-api, adds business logic."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.middleware.auth import get_current_user
from app.infrastructure.clients.email_client import smart_label_client
from app.presentation.schemas.smart_label_schemas import (
    SmartLabelCreate,
    SmartLabelUpdate,
    SmartLabelResponse,
    SmartLabelListResponse,
)

router = APIRouter(prefix="/inbox/labels")


@router.post("", response_model=SmartLabelResponse, status_code=status.HTTP_201_CREATED)
async def create_smart_label(
    data: SmartLabelCreate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    result = await smart_label_client.create(data.model_dump(), forward_headers=request.headers)
    return result


@router.get("", response_model=SmartLabelListResponse)
async def list_smart_labels(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
):
    return await smart_label_client.list(skip, limit, forward_headers=request.headers)


@router.get("/{label_id}", response_model=SmartLabelResponse)
async def get_smart_label(
    label_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    label = await smart_label_client.get(label_id, forward_headers=request.headers)
    if not label:
        raise HTTPException(status_code=404, detail="Smart label not found")
    return label


@router.patch("/{label_id}", response_model=SmartLabelResponse)
async def update_smart_label(
    label_id: str,
    data: SmartLabelUpdate,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    update_data = data.model_dump(exclude_unset=True)
    result = await smart_label_client.update(label_id, update_data, forward_headers=request.headers)
    return result


@router.delete("/{label_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_smart_label(
    label_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    deleted = await smart_label_client.delete(label_id, forward_headers=request.headers)
    if not deleted:
        raise HTTPException(status_code=404, detail="Smart label not found")
