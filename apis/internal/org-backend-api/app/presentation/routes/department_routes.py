"""Department HTTP routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from app.application.use_cases.department_use_cases import DepartmentUseCases
from app.domain.exceptions import DepartmentNotFoundError
from app.middleware.auth import get_current_user
from app.presentation.deps import get_department_use_cases
from app.presentation.schemas.department_schemas import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
)

router = APIRouter(prefix="/api/v1/departments")


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    user: dict = Depends(get_current_user),
    use_cases: DepartmentUseCases = Depends(get_department_use_cases),
):
    items = await use_cases.list_departments(user["tenant_id"])
    return [DepartmentResponse.model_validate(d) for d in items]


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    user: dict = Depends(get_current_user),
    use_cases: DepartmentUseCases = Depends(get_department_use_cases),
):
    created = await use_cases.create_department(data.model_dump(), user)
    return DepartmentResponse.model_validate(created)


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: str,
    user: dict = Depends(get_current_user),
    use_cases: DepartmentUseCases = Depends(get_department_use_cases),
):
    try:
        dept = await use_cases.get_department(dept_id, user["tenant_id"])
    except DepartmentNotFoundError:
        raise HTTPException(status_code=404, detail="Department not found")
    return DepartmentResponse.model_validate(dept)


@router.patch("/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: str, data: DepartmentUpdate,
    user: dict = Depends(get_current_user),
    use_cases: DepartmentUseCases = Depends(get_department_use_cases),
):
    try:
        updated = await use_cases.update_department(
            dept_id,
            data.model_dump(exclude_unset=True),
            user,
        )
    except DepartmentNotFoundError:
        raise HTTPException(status_code=404, detail="Department not found")
    return DepartmentResponse.model_validate(updated)


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: str,
    user: dict = Depends(get_current_user),
    use_cases: DepartmentUseCases = Depends(get_department_use_cases),
):
    try:
        await use_cases.delete_department(dept_id, user)
    except DepartmentNotFoundError:
        raise HTTPException(status_code=404, detail="Department not found")
