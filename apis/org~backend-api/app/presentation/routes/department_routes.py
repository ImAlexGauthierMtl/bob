"""Department CRUD routes — pure storage, no business logic."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.middleware.auth import get_current_user
from app.infrastructure.persistence.department_repository import DepartmentRepository
from app.domain.entities.department import Department
from app.presentation.schemas.department_schemas import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
)

router = APIRouter(prefix="/api/v1/departments")


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = DepartmentRepository(db)
    items = repo.list_all(user["tenant_id"])
    return [DepartmentResponse.model_validate(d) for d in items]


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = DepartmentRepository(db)
    dept = Department(**data.model_dump(), tenant_id=user["tenant_id"], created_by=user["email"])
    return DepartmentResponse.model_validate(repo.create(dept))


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = DepartmentRepository(db)
    dept = repo.get_by_id(dept_id, user["tenant_id"])
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return DepartmentResponse.model_validate(dept)


@router.patch("/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: str, data: DepartmentUpdate,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = DepartmentRepository(db)
    dept = repo.get_by_id(dept_id, user["tenant_id"])
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(dept, k, v)
    return DepartmentResponse.model_validate(repo.update(dept))


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: str,
    user: dict = Depends(get_current_user), db: Session = Depends(get_db),
):
    repo = DepartmentRepository(db)
    dept = repo.get_by_id(dept_id, user["tenant_id"])
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    repo.soft_delete(dept, user["email"])
