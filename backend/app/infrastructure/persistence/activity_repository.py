"""Activity repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.activity import Activity
from app.domain.entities.organization import Organization
from app.domain.entities.contact import Contact
from app.domain.entities.opportunity import Opportunity


class ActivityRepository:
    """Repository for activity data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, activity: dict, tenant_id: str) -> Activity:
        # We assume the caller passes a dict with the raw payload
        db_activity = Activity(
            tenant_id=tenant_id,
            subject=activity.get("subject"),
            description=activity.get("description"),
            activity_type=activity.get("activity_type"),
            priority=activity.get("priority"),
            status=activity.get("status"),
            due_date=activity.get("due_date"),
            assigned_to=activity.get("assigned_to"),
            owner_id=activity.get("owner_id"),
        )
        
        # Link organizations
        org_ids = activity.get("organization_ids", [])
        if org_ids:
            orgs = self.db.query(Organization).filter(Organization.id.in_(org_ids), Organization.tenant_id == tenant_id, Organization.is_deleted == False).all()
            db_activity.organizations.extend(orgs)
            
        # Link contacts
        contact_ids = activity.get("contact_ids", [])
        if contact_ids:
            contacts = self.db.query(Contact).filter(Contact.id.in_(contact_ids), Contact.tenant_id == tenant_id, Contact.is_deleted == False).all()
            db_activity.contacts.extend(contacts)
            
        # Link opportunities
        opp_ids = activity.get("opportunity_ids", [])
        if opp_ids:
            opps = self.db.query(Opportunity).filter(Opportunity.id.in_(opp_ids), Opportunity.tenant_id == tenant_id, Opportunity.is_deleted == False).all()
            db_activity.opportunities.extend(opps)

        self.db.add(db_activity)
        self.db.commit()
        self.db.refresh(db_activity)
        return db_activity

    def get_by_id(self, activity_id: str, tenant_id: str) -> Optional[Activity]:
        return self.db.query(Activity).filter(
            Activity.id == activity_id,
            Activity.tenant_id == tenant_id,
            Activity.is_deleted == False,
        ).first()

    def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50, organization_id: Optional[str] = None, contact_id: Optional[str] = None, opportunity_id: Optional[str] = None, status: Optional[str] = None) -> List[Activity]:
        query = self.db.query(Activity).filter(Activity.tenant_id == tenant_id, Activity.is_deleted == False)
        if organization_id:
            query = query.filter(Activity.organizations.any(id=organization_id))
        if contact_id:
            query = query.filter(Activity.contacts.any(id=contact_id))
        if opportunity_id:
            query = query.filter(Activity.opportunities.any(id=opportunity_id))
        if status:
            query = query.filter(Activity.status == status)
        return query.order_by(Activity.due_date.desc().nullslast()).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, organization_id: Optional[str] = None, contact_id: Optional[str] = None, opportunity_id: Optional[str] = None, status: Optional[str] = None) -> int:
        query = self.db.query(Activity).filter(Activity.tenant_id == tenant_id, Activity.is_deleted == False)
        if organization_id:
            query = query.filter(Activity.organizations.any(id=organization_id))
        if contact_id:
            query = query.filter(Activity.contacts.any(id=contact_id))
        if opportunity_id:
            query = query.filter(Activity.opportunities.any(id=opportunity_id))
        if status:
            query = query.filter(Activity.status == status)
        return query.count()

    def update(self, activity: Activity, payload: dict = None) -> Activity:
        if payload is not None:
            # We assume regular fields are updated on the activity object outside, 
            # we just handle M:N relations here if provided
            org_ids = payload.get("organization_ids")
            if org_ids is not None:
                orgs = self.db.query(Organization).filter(Organization.id.in_(org_ids), Organization.tenant_id == activity.tenant_id, Organization.is_deleted == False).all()
                activity.organizations = orgs
                
            contact_ids = payload.get("contact_ids")
            if contact_ids is not None:
                contacts = self.db.query(Contact).filter(Contact.id.in_(contact_ids), Contact.tenant_id == activity.tenant_id, Contact.is_deleted == False).all()
                activity.contacts = contacts
                
            opp_ids = payload.get("opportunity_ids")
            if opp_ids is not None:
                opps = self.db.query(Opportunity).filter(Opportunity.id.in_(opp_ids), Opportunity.tenant_id == activity.tenant_id, Opportunity.is_deleted == False).all()
                activity.opportunities = opps
                
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
