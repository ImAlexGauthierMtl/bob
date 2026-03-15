"""Smart Label repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import exc

from app.domain.entities.smart_label import SmartLabel


class SmartLabelRepository:
    """Repository for smart label data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, label: SmartLabel) -> SmartLabel:
        """Create a new smart label."""
        self.db.add(label)
        self.db.commit()
        self.db.refresh(label)
        return label

    def get_by_id(self, label_id: str, tenant_id: str) -> Optional[SmartLabel]:
        """Get smart label by ID (tenant-scoped)."""
        return self.db.query(SmartLabel).filter(
            SmartLabel.id == label_id,
            SmartLabel.tenant_id == tenant_id,
        ).first()

    def get_by_name(self, name: str, tenant_id: str, parent_id: Optional[str] = None) -> Optional[SmartLabel]:
        """Get smart label by explicit name (tenant-scoped and parent-scoped)."""
        query = self.db.query(SmartLabel).filter(
            SmartLabel.name == name,
            SmartLabel.tenant_id == tenant_id,
        )
        if parent_id is not None:
            query = query.filter(SmartLabel.parent_id == parent_id)
        else:
            query = query.filter(SmartLabel.parent_id.is_(None))
        return query.first()

    def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50) -> List[SmartLabel]:
        """List root smart labels with pagination (tenant-scoped). Sub-labels are eager loaded."""
        from sqlalchemy.orm import selectinload
        return self.db.query(SmartLabel).filter(
            SmartLabel.tenant_id == tenant_id,
            SmartLabel.parent_id.is_(None)
        ).options(
            selectinload(SmartLabel.sub_labels)
        ).order_by(SmartLabel.created_at.desc()).offset(skip).limit(limit).all()

    def count(self, tenant_id: str) -> int:
        """Count root smart labels (tenant-scoped)."""
        return self.db.query(SmartLabel).filter(
            SmartLabel.tenant_id == tenant_id,
            SmartLabel.parent_id.is_(None)
        ).count()

    def update(self, label: SmartLabel) -> SmartLabel:
        """Update a smart label."""
        label.version += 1
        self.db.commit()
        self.db.refresh(label)
        return label

    def delete(self, label: SmartLabel) -> None:
        """Hard delete a smart label (no soft delete required)."""
        try:
            self.db.delete(label)
            self.db.commit()
        except exc.IntegrityError:
            self.db.rollback()
            raise ValueError("Cannot delete smart label, it may be in use.")
