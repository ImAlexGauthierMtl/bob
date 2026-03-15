"""Department repository — data access layer."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.domain.entities.department import Department


class DepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, dept: Department) -> Department:
        self.db.add(dept)
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def get_by_id(self, dept_id: str, tenant_id: str) -> Optional[Department]:
        return self.db.query(Department).filter(
            Department.id == dept_id,
            Department.tenant_id == tenant_id,
            Department.is_deleted == False,
        ).first()

    def list_all(self, tenant_id: str) -> List[Department]:
        return self.db.query(Department).filter(
            Department.tenant_id == tenant_id, Department.is_deleted == False,
        ).order_by(Department.name).all()

    def update(self, dept: Department) -> Department:
        dept.version += 1
        self.db.commit()
        self.db.refresh(dept)
        return dept

    def soft_delete(self, dept: Department, deleted_by: str) -> Department:
        from datetime import datetime, timezone
        dept.is_deleted = True
        dept.deleted_at = datetime.now(timezone.utc)
        dept.deleted_by = deleted_by
        dept.version += 1
        self.db.commit()
        self.db.refresh(dept)
        return dept
