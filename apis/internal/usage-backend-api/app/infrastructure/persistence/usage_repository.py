"""Usage repository — data access layer."""

from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.infrastructure.persistence.models.usage_transaction import UsageTransaction, CostRateCard


class UsageRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Record ────────────────────────────────

    def record(self, txn: UsageTransaction) -> UsageTransaction:
        self.db.add(txn)
        self.db.commit()
        self.db.refresh(txn)
        return txn

    # ── List / Filter ─────────────────────────

    def list_by_tenant(
        self,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        service_type: Optional[str] = None,
        billing_category: Optional[str] = None,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[UsageTransaction]:
        query = self.db.query(UsageTransaction)
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)
        query = self._apply_filters(query, service_type, billing_category, user_id, date_from, date_to)
        return query.order_by(UsageTransaction.timestamp.desc()).offset(skip).limit(limit).all()

    def count_by_tenant(
        self,
        tenant_id: Optional[str] = None,
        service_type: Optional[str] = None,
        billing_category: Optional[str] = None,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        query = self.db.query(UsageTransaction)
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)
        query = self._apply_filters(query, service_type, billing_category, user_id, date_from, date_to)
        return query.count()

    def _apply_filters(self, query, service_type, billing_category, user_id, date_from, date_to):
        if service_type:
            query = query.filter(UsageTransaction.service_type == service_type)
        if billing_category:
            query = query.filter(UsageTransaction.billing_category == billing_category)
        if user_id:
            query = query.filter(UsageTransaction.user_id == user_id)
        if date_from:
            query = query.filter(UsageTransaction.timestamp >= date_from)
        if date_to:
            query = query.filter(UsageTransaction.timestamp <= date_to)
        return query

    # ── Summary ───────────────────────────────

    def get_summary(
        self,
        tenant_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[dict]:
        query = self.db.query(
            UsageTransaction.service_type,
            UsageTransaction.billing_category,
            func.count(UsageTransaction.id).label("transaction_count"),
            func.coalesce(func.sum(UsageTransaction.cogs_amount), 0).label("total_cogs"),
            func.coalesce(func.sum(UsageTransaction.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(UsageTransaction.output_tokens), 0).label("total_output_tokens"),
        ).filter(UsageTransaction.tenant_id == tenant_id)

        if date_from:
            query = query.filter(UsageTransaction.timestamp >= date_from)
        if date_to:
            query = query.filter(UsageTransaction.timestamp <= date_to)

        rows = query.group_by(
            UsageTransaction.service_type,
            UsageTransaction.billing_category,
        ).all()

        return [
            {
                "service_type": r.service_type.value if r.service_type else None,
                "billing_category": r.billing_category.value if r.billing_category else None,
                "transaction_count": r.transaction_count,
                "total_cogs": float(r.total_cogs),
                "total_input_tokens": r.total_input_tokens,
                "total_output_tokens": r.total_output_tokens,
            }
            for r in rows
        ]

    # ── Correlation ───────────────────────────

    def list_by_correlation(
        self,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        query = self.db.query(
            UsageTransaction.correlation_id,
            UsageTransaction.correlation_label,
            func.count(UsageTransaction.id).label("transaction_count"),
            func.coalesce(func.sum(UsageTransaction.cogs_amount), 0).label("total_cogs"),
            func.min(UsageTransaction.timestamp).label("first_at"),
            func.max(UsageTransaction.timestamp).label("last_at"),
        ).filter(UsageTransaction.correlation_id.isnot(None))

        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)

        rows = query.group_by(
            UsageTransaction.correlation_id,
            UsageTransaction.correlation_label,
        ).order_by(func.max(UsageTransaction.timestamp).desc()).offset(skip).limit(limit).all()

        return [
            {
                "correlation_id": r.correlation_id,
                "correlation_label": r.correlation_label,
                "transaction_count": r.transaction_count,
                "total_cogs": float(r.total_cogs),
                "first_at": str(r.first_at) if r.first_at else None,
                "last_at": str(r.last_at) if r.last_at else None,
            }
            for r in rows
        ]

    def count_by_correlation(self, tenant_id: Optional[str] = None) -> int:
        query = self.db.query(func.count(func.distinct(UsageTransaction.correlation_id))).filter(
            UsageTransaction.correlation_id.isnot(None)
        )
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)
        return query.scalar() or 0

    def sum_cogs_by_correlation(self, tenant_id: Optional[str] = None) -> float:
        query = self.db.query(func.coalesce(func.sum(UsageTransaction.cogs_amount), 0)).filter(
            UsageTransaction.correlation_id.isnot(None)
        )
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)
        return float(query.scalar() or 0)

    def list_by_correlation_id(self, correlation_id: str) -> List[UsageTransaction]:
        return self.db.query(UsageTransaction).filter(
            UsageTransaction.correlation_id == correlation_id,
        ).order_by(UsageTransaction.timestamp).all()

    # ── Rate Cards ────────────────────────────

    def create_rate_card(self, card: CostRateCard) -> CostRateCard:
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return card

    def list_rate_cards(self, active_only: bool = True) -> List[CostRateCard]:
        query = self.db.query(CostRateCard)
        if active_only:
            query = query.filter(CostRateCard.effective_to.is_(None))
        return query.order_by(CostRateCard.provider, CostRateCard.model).all()

    def get_rate_card(self, card_id: str) -> Optional[CostRateCard]:
        return self.db.query(CostRateCard).filter(CostRateCard.id == card_id).first()
