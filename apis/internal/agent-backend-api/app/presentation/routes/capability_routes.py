"""Capability routes — CRUD for capability definitions and user capability assignments."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.use_cases.capability_use_cases import CapabilityUseCases
from app.domain.exceptions import CapabilityNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_capability_use_cases
from app.presentation.schemas.capability_schemas import (
    CapabilityDefinitionResponse,
    UserCapabilityAssign,
    UserCapabilitiesResponse,
)

router = APIRouter(prefix="/api/v1/capabilities")


@router.get("/catalog", response_model=list[CapabilityDefinitionResponse])
async def list_capability_catalog(
    current_user: dict = Depends(get_current_user),
    use_cases: CapabilityUseCases = Depends(get_capability_use_cases),
):
    return await use_cases.list_catalog()


@router.get("/users/{user_id}", response_model=UserCapabilitiesResponse)
async def get_user_capabilities(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: CapabilityUseCases = Depends(get_capability_use_cases),
):
    return await use_cases.get_user_capabilities(user_id, current_user["tenant_id"])


@router.get("/me", response_model=UserCapabilitiesResponse)
async def get_my_capabilities(
    current_user: dict = Depends(get_current_user),
    use_cases: CapabilityUseCases = Depends(get_capability_use_cases),
):
    return await use_cases.get_user_capabilities(current_user["user_id"], current_user["tenant_id"])


@router.post("/users/{user_id}/assign", status_code=status.HTTP_201_CREATED)
async def assign_capability(
    user_id: str, data: UserCapabilityAssign,
    current_user: dict = Depends(get_current_user),
    use_cases: CapabilityUseCases = Depends(get_capability_use_cases),
):
    try:
        return await use_cases.assign_capability(user_id, data.model_dump(), current_user)
    except CapabilityNotFoundError:
        raise HTTPException(status_code=404, detail=f"Capability '{data.capability_code}' not found")


@router.post("/check")
async def check_capability(
    capability_code: str,
    current_user: dict = Depends(get_current_user),
    use_cases: CapabilityUseCases = Depends(get_capability_use_cases),
):
    return await use_cases.check_capability(capability_code, current_user)
