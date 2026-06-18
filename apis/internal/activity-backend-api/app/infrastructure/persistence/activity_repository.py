"""Activity repository — data access layer (simplified, no M:N joins)."""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import cast, String
from app.infrastructure.persistence.models.activity import Activity


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, activity: Activity) -> Activity:
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def get_by_id(self, activity_id: str, tenant_id: str) -> Optional[Activity]:
        return self.db.query(Activity).filter(
            Activity.id == activity_id,
            Activity.tenant_id == tenant_id,
            Activity.is_deleted == False,
        ).first()

    def list_all(
        self, tenant_id: str, skip: int = 0, limit: int = 50,
        status: Optional[str] = None,
    ) -> List[Activity]:
        q = self.db.query(Activity).filter(Activity.tenant_id == tenant_id, Activity.is_deleted == False)
        if status:
            q = q.filter(Activity.status == status)
        return q.order_by(Activity.due_date.desc().nullslast()).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, status: Optional[str] = None) -> int:
        q = self.db.query(Activity).filter(Activity.tenant_id == tenant_id, Activity.is_deleted == False)
        if status:
            q = q.filter(Activity.status == status)
        return q.count()

    def update(self, activity: Activity) -> Activity:
        activity.version += 1
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def soft_delete(self, activity: Activity, deleted_by: str, reason: Optional[str] = None) -> Activity:
        from datetime import datetime, timezone
        activity.is_deleted = True
        activity.deleted_at = datetime.now(timezone.utc)
        activity.deleted_by = deleted_by
        activity.deleted_reason = reason
        activity.version += 1
        self.db.commit()
        self.db.refresh(activity)
        return activity
