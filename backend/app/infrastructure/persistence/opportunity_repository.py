"""Opportunity repository — data access layer."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.opportunity import Opportunity


class OpportunityRepository:
    """Repository for opportunity data access."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, opp: Opportunity) -> Opportunity:
        self.db.add(opp)
        self.db.commit()
        self.db.refresh(opp)
        return opp

    def get_by_id(self, opp_id: str, tenant_id: str) -> Optional[Opportunity]:
        return self.db.query(Opportunity).filter(
            Opportunity.id == opp_id,
            Opportunity.tenant_id == tenant_id,
            Opportunity.is_deleted == False,
        ).first()

    def list_all(self, tenant_id: str, skip: int = 0, limit: int = 50, organization_id: Optional[str] = None, stage: Optional[str] = None) -> List[Opportunity]:
        query = self.db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id, Opportunity.is_deleted == False)
        if organization_id:
            query = query.filter(Opportunity.organization_id == organization_id)
        if stage:
            query = query.filter(Opportunity.stage == stage)
        return query.order_by(Opportunity.created_at.desc()).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, organization_id: Optional[str] = None) -> int:
        query = self.db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id, Opportunity.is_deleted == False)
        if organization_id:
            query = query.filter(Opportunity.organization_id == organization_id)
        return query.count()

    def update(self, opp: Opportunity) -> Opportunity:
        opp.version += 1
        self.db.commit()
        self.db.refresh(opp)
        return opp

    def soft_delete(self, opp: Opportunity, deleted_by: str, reason: Optional[str] = None) -> Opportunity:
        from datetime import datetime, timezone
        opp.is_deleted = True
        opp.deleted_at = datetime.now(timezone.utc)
        opp.deleted_by = deleted_by
        opp.deleted_reason = reason
        opp.version += 1
        self.db.commit()
        self.db.refresh(opp)
        return opp
