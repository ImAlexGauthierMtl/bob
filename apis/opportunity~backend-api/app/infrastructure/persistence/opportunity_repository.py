"""Opportunity repository — data access layer."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.domain.entities.opportunity import Opportunity
from app.domain.entities.opportunity_product import OpportunityProduct


class OpportunityRepository:
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

    def list_all(
        self, tenant_id: str, skip: int = 0, limit: int = 50,
        organization_id: Optional[str] = None, stage: Optional[str] = None,
    ) -> List[Opportunity]:
        q = self.db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id, Opportunity.is_deleted == False)
        if organization_id:
            q = q.filter(Opportunity.organization_id == organization_id)
        if stage:
            q = q.filter(Opportunity.stage == stage)
        return q.order_by(Opportunity.created_at.desc()).offset(skip).limit(limit).all()

    def count(self, tenant_id: str, organization_id: Optional[str] = None) -> int:
        q = self.db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id, Opportunity.is_deleted == False)
        if organization_id:
            q = q.filter(Opportunity.organization_id == organization_id)
        return q.count()

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

    def add_product(self, line_item: OpportunityProduct) -> OpportunityProduct:
        self.db.add(line_item)
        self.db.commit()
        self.db.refresh(line_item)
        return line_item

    def list_products(self, opp_id: str, tenant_id: str) -> List[OpportunityProduct]:
        return self.db.query(OpportunityProduct).filter(
            OpportunityProduct.opportunity_id == opp_id,
            OpportunityProduct.tenant_id == tenant_id,
        ).all()

    def get_product_line(self, line_id: str, tenant_id: str) -> Optional[OpportunityProduct]:
        return self.db.query(OpportunityProduct).filter(
            OpportunityProduct.id == line_id,
            OpportunityProduct.tenant_id == tenant_id,
        ).first()

    def remove_product(self, line_item: OpportunityProduct) -> None:
        self.db.delete(line_item)
        self.db.commit()
