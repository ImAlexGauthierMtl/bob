"""Activity repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.activity import Activity


class ActivityRepository:
    """Repository for activity data access."""

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

    def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50, organization_id: Optional[str] = None, contact_id: Optional[str] = None, opportunity_id: Optional[str] = None, status: Optional[str] = None) -> List[Activity]:
        query = self.db.query(Activity).filter(Activity.tenant_id == tenant_id, Activity.is_deleted == False)
        if organization_id:
            query = query.filter(Activity.organization_id == organization_id)
        if contact_id:
            query = query.filter(Activity.contact_id == contact_id)
        if opportunity_id:
            query = query.filter(Activity.opportunity_id == opportunity_id)
        if status:
            query = query.filter(Activity.status == status)
        return query.order_by(Activity.due_date.desc().nullslast()).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, organization_id: Optional[str] = None, contact_id: Optional[str] = None, opportunity_id: Optional[str] = None, status: Optional[str] = None) -> int:
        query = self.db.query(Activity).filter(Activity.tenant_id == tenant_id, Activity.is_deleted == False)
        if organization_id:
            query = query.filter(Activity.organization_id == organization_id)
        if contact_id:
            query = query.filter(Activity.contact_id == contact_id)
        if opportunity_id:
            query = query.filter(Activity.opportunity_id == opportunity_id)
        if status:
            query = query.filter(Activity.status == status)
        return query.count()

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
