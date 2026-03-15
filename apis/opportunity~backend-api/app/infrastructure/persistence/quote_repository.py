"""Quote repository — data access layer."""
from typing import Optional, List
from sqlalchemy.orm import Session
from app.domain.entities.quote import Quote


class QuoteRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, quote: Quote) -> Quote:
        self.db.add(quote)
        self.db.commit()
        self.db.refresh(quote)
        return quote

    def get_by_id(self, quote_id: str, tenant_id: str) -> Optional[Quote]:
        return self.db.query(Quote).filter(
            Quote.id == quote_id,
            Quote.tenant_id == tenant_id,
            Quote.is_deleted == False,
        ).first()

    def list_all(
        self, tenant_id: str, skip: int = 0, limit: int = 50, opportunity_id: Optional[str] = None,
    ) -> List[Quote]:
        q = self.db.query(Quote).filter(Quote.tenant_id == tenant_id, Quote.is_deleted == False)
        if opportunity_id:
            q = q.filter(Quote.opportunity_id == opportunity_id)
        return q.order_by(Quote.created_at.desc()).offset(skip).limit(limit).all()

    def count(self, tenant_id: str) -> int:
        return self.db.query(Quote).filter(Quote.tenant_id == tenant_id, Quote.is_deleted == False).count()

    def update(self, quote: Quote) -> Quote:
        quote.version += 1
        self.db.commit()
        self.db.refresh(quote)
        return quote

    def soft_delete(self, quote: Quote, deleted_by: str, reason: Optional[str] = None) -> Quote:
        from datetime import datetime, timezone
        quote.is_deleted = True
        quote.deleted_at = datetime.now(timezone.utc)
        quote.deleted_by = deleted_by
        quote.deleted_reason = reason
        quote.version += 1
        self.db.commit()
        self.db.refresh(quote)
        return quote
