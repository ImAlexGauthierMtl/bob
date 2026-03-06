"""Department routes — CRUD + member management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.presentation.routes.auth_routes import get_current_user
from app.infrastructure.persistence.department_repository import DepartmentRepository
from app.domain.entities.department import Department
from app.presentation.schemas.department_schemas import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentListResponse,
    DepartmentMemberAdd,
    DepartmentMemberResponse,
)

router = APIRouter(prefix="/api/v1/departments")


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department(
    data: DepartmentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new department."""
    repo = DepartmentRepository(db)
    dept = Department(
        name=data.name,
        description=data.description,
        manager_user_id=data.manager_user_id,
        tenant_id=current_user["tenant_id"],
        created_by=current_user["email"],
    )
    return repo.create(dept)


@router.get("", response_model=DepartmentListResponse)
async def list_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all departments."""
    repo = DepartmentRepository(db)
    items = repo.list_all(current_user["tenant_id"], skip, limit)
    total = repo.count(current_user["tenant_id"])
    return DepartmentListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a department by ID."""
    repo = DepartmentRepository(db)
    dept = repo.get_by_id(dept_id, current_user["tenant_id"])
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.patch("/{dept_id}", response_model=DepartmentResponse)
async def update_department(
    dept_id: str,
    data: DepartmentUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a department."""
    repo = DepartmentRepository(db)
    dept = repo.get_by_id(dept_id, current_user["tenant_id"])
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(dept, key, value)
    dept.updated_by = current_user["email"]
    return repo.update(dept)


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Soft delete a department."""
    repo = DepartmentRepository(db)
    dept = repo.get_by_id(dept_id, current_user["tenant_id"])
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    repo.soft_delete(dept, current_user["email"])


# ── Members ──────────────────────────────────────

@router.post("/{dept_id}/members", response_model=DepartmentMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    dept_id: str,
    data: DepartmentMemberAdd,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a user to a department."""
    repo = DepartmentRepository(db)
    dept = repo.get_by_id(dept_id, current_user["tenant_id"])
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    ud = repo.add_user(data.user_id, dept_id, data.is_manager)
    return DepartmentMemberResponse(
        user_id=ud.user_id,
        department_id=ud.department_id,
        is_manager=ud.is_manager,
    )


@router.delete("/{dept_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    dept_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a user from a department."""
    repo = DepartmentRepository(db)
    repo.remove_user(user_id, dept_id)
