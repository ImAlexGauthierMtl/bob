"""Activity HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.application.use_cases.activity_use_cases import ActivityUseCases
from app.domain.exceptions import ActivityNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_activity_use_cases
from app.presentation.schemas.activity_schemas import (
    ActivityCreate, ActivityUpdate, ActivityResponse, ActivityListResponse,
)

router = APIRouter(prefix="/api/v1/activities")


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    skip: int = 0, limit: int = 50, status_filter: str = Query(None, alias="status"),
    user: dict = Depends(get_current_user),
    use_cases: ActivityUseCases = Depends(get_activity_use_cases),
):
    result = await use_cases.list_activities(user["tenant_id"], skip, limit, status_filter)
    return ActivityListResponse(
        items=[ActivityResponse.model_validate(activity) for activity in result.items],
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    data: ActivityCreate,
    user: dict = Depends(get_current_user),
    use_cases: ActivityUseCases = Depends(get_activity_use_cases),
):
    created = await use_cases.create_activity(data.model_dump(), user)
    return ActivityResponse.model_validate(created)


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: str,
    user: dict = Depends(get_current_user),
    use_cases: ActivityUseCases = Depends(get_activity_use_cases),
):
    try:
        activity = await use_cases.get_activity(activity_id, user["tenant_id"])
    except ActivityNotFoundError:
        raise HTTPException(status_code=404, detail="Activity not found")
    return ActivityResponse.model_validate(activity)


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity(
    activity_id: str, data: ActivityUpdate,
    user: dict = Depends(get_current_user),
    use_cases: ActivityUseCases = Depends(get_activity_use_cases),
):
    try:
        updated = await use_cases.update_activity(
            activity_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except ActivityNotFoundError:
        raise HTTPException(status_code=404, detail="Activity not found")
    return ActivityResponse.model_validate(updated)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_activity(
    activity_id: str,
    user: dict = Depends(get_current_user),
    use_cases: ActivityUseCases = Depends(get_activity_use_cases),
):
    try:
        await use_cases.delete_activity(activity_id, user)
    except ActivityNotFoundError:
        raise HTTPException(status_code=404, detail="Activity not found")
