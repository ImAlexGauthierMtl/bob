"""Activity repository."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.domain.entities.activity import Activity
from app.domain.entities.organization import Organization
from app.domain.entities.contact import Contact
from app.domain.entities.opportunity import Opportunity

class ActivityRepository:
    def __init__(self, db: Session): self.db = db
    def create(self, activity: dict, tenant_id: str) -> Activity:
        db_activity = Activity(tenant_id=tenant_id, subject=activity.get("subject"), description=activity.get("description"),
            activity_type=activity.get("activity_type"), priority=activity.get("priority"), status=activity.get("status"),
            due_date=activity.get("due_date"), assigned_to=activity.get("assigned_to"), owner_id=activity.get("owner_id"))
        for ids, model, rel in [("organization_ids", Organization, db_activity.organizations),
                                 ("contact_ids", Contact, db_activity.contacts),
                                 ("opportunity_ids", Opportunity, db_activity.opportunities)]:
            entity_ids = activity.get(ids, [])
            if entity_ids:
                entities = self.db.query(model).filter(model.id.in_(entity_ids), model.tenant_id == tenant_id, model.is_deleted == False).all()
                rel.extend(entities)
        self.db.add(db_activity); self.db.commit(); self.db.refresh(db_activity); return db_activity

    def get_by_id(self, activity_id: str, tenant_id: str) -> Optional[Activity]:
        return self.db.query(Activity).filter(Activity.id == activity_id, Activity.tenant_id == tenant_id, Activity.is_deleted == False).first()

    def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50, organization_id: Optional[str] = None,
                 contact_id: Optional[str] = None, opportunity_id: Optional[str] = None, status: Optional[str] = None) -> List[Activity]:
        q = self.db.query(Activity).filter(Activity.tenant_id == tenant_id, Activity.is_deleted == False)
        if organization_id: q = q.filter(Activity.organizations.any(id=organization_id))
        if contact_id: q = q.filter(Activity.contacts.any(id=contact_id))
        if opportunity_id: q = q.filter(Activity.opportunities.any(id=opportunity_id))
        if status: q = q.filter(Activity.status == status)
        return q.order_by(Activity.due_date.desc().nullslast()).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, organization_id: Optional[str] = None, contact_id: Optional[str] = None,
              opportunity_id: Optional[str] = None, status: Optional[str] = None) -> int:
        q = self.db.query(Activity).filter(Activity.tenant_id == tenant_id, Activity.is_deleted == False)
        if organization_id: q = q.filter(Activity.organizations.any(id=organization_id))
        if contact_id: q = q.filter(Activity.contacts.any(id=contact_id))
        if opportunity_id: q = q.filter(Activity.opportunities.any(id=opportunity_id))
        if status: q = q.filter(Activity.status == status)
        return q.count()

    def update(self, activity: Activity, payload: dict = None) -> Activity:
        if payload:
            for ids, model, attr in [("organization_ids", Organization, "organizations"),
                                      ("contact_ids", Contact, "contacts"),
                                      ("opportunity_ids", Opportunity, "opportunities")]:
                entity_ids = payload.get(ids)
                if entity_ids is not None:
                    entities = self.db.query(model).filter(model.id.in_(entity_ids), model.tenant_id == activity.tenant_id, model.is_deleted == False).all()
                    setattr(activity, attr, entities)
        activity.version += 1; self.db.commit(); self.db.refresh(activity); return activity

    def soft_delete(self, activity: Activity, deleted_by: str, reason: Optional[str] = None) -> Activity:
        from datetime import datetime, timezone
        activity.is_deleted = True; activity.deleted_at = datetime.now(timezone.utc); activity.deleted_by = deleted_by; activity.deleted_reason = reason; activity.version += 1
        self.db.commit(); self.db.refresh(activity); return activity
