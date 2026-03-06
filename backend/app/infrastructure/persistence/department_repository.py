"""Department repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.department import Department, UserDepartment


class DepartmentRepository:
    """Repository for department data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, dept: Department) -> Department:
        """Create a new department."""
        self.db.add(dept)
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def get_by_id(self, dept_id: str, tenant_id: str) -> Optional[Department]:
        """Get department by ID (tenant-scoped)."""
        return self.db.query(Department).filter(
            Department.id == dept_id,
            Department.tenant_id == tenant_id,
            Department.is_deleted == False,
        ).first()

    def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50) -> List[Department]:
        """List departments with pagination (tenant-scoped)."""
        return self.db.query(Department).filter(
            Department.tenant_id == tenant_id,
            Department.is_deleted == False,
        ).order_by(Department.name).offset(skip).limit(limit).all()

    def count(self, tenant_id: str) -> int:
        """Count departments (tenant-scoped)."""
        return self.db.query(Department).filter(
            Department.tenant_id == tenant_id,
            Department.is_deleted == False,
        ).count()

    def update(self, dept: Department) -> Department:
        """Update a department."""
        dept.version += 1
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def soft_delete(self, dept: Department, deleted_by: str) -> Department:
        """Soft delete a department."""
        from datetime import datetime, timezone
        dept.is_deleted = True
        dept.deleted_at = datetime.now(timezone.utc)
        dept.deleted_by = deleted_by
        dept.version += 1
        self.db.commit()
        self.db.refresh(dept)
        return dept

    # ── User-Department M:N ──────────────────────

    def add_user(self, user_id: str, department_id: str, is_manager: bool = False) -> UserDepartment:
        """Add a user to a department."""
        ud = UserDepartment(
            user_id=user_id,
            department_id=department_id,
            is_manager="true" if is_manager else "false",
        )
        self.db.add(ud)
        self.db.commit()
        self.db.refresh(ud)
        return ud

    def remove_user(self, user_id: str, department_id: str) -> None:
        """Remove a user from a department."""
        self.db.query(UserDepartment).filter(
            UserDepartment.user_id == user_id,
            UserDepartment.department_id == department_id,
        ).delete()
        self.db.commit()

    def get_user_departments(self, user_id: str) -> List[Department]:
        """Get all departments for a user."""
        dept_ids = [
            ud.department_id for ud in
            self.db.query(UserDepartment).filter(
                UserDepartment.user_id == user_id,
            ).all()
        ]
        if not dept_ids:
            return []
        return self.db.query(Department).filter(
            Department.id.in_(dept_ids),
            Department.is_deleted == False,
        ).all()

    def get_department_members(self, department_id: str) -> List[UserDepartment]:
        """Get all users in a department."""
        return self.db.query(UserDepartment).filter(
            UserDepartment.department_id == department_id,
        ).all()
