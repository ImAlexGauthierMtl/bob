"""Usage repository — data access layer for usage transactions and rate cards."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.domain.entities.usage_transaction import (
    UsageTransaction, CostRateCard, ServiceType, BillingCategory,
)


class UsageRepository:
    """Repository for usage transaction data access (append-only)."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, transaction: UsageTransaction) -> UsageTransaction:
        """Insert a usage transaction (append-only — no update or delete)."""
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def list_by_tenant(
        self,
        tenant_id: Optional[str],
        skip: int = 0,
        limit: int = 50,
        service_type: Optional[str] = None,
        billing_category: Optional[str] = None,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[UsageTransaction]:
        """List usage transactions with optional filters."""
        query = self.db.query(UsageTransaction)
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)
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
        return query.order_by(UsageTransaction.timestamp.desc()).offset(skip).limit(limit).all()

    def count_by_tenant(
        self,
        tenant_id: Optional[str],
        service_type: Optional[str] = None,
        billing_category: Optional[str] = None,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        """Count usage transactions with optional filters."""
        query = self.db.query(UsageTransaction)
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)
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
        return query.count()

    def get_summary(
        self,
        tenant_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[dict]:
        """Get usage summary aggregated by service_type and billing_category."""
        query = self.db.query(
            UsageTransaction.service_type,
            UsageTransaction.billing_category,
            func.count(UsageTransaction.id).label("transaction_count"),
            func.sum(UsageTransaction.cogs_amount).label("total_cogs"),
            func.sum(UsageTransaction.input_tokens).label("total_input_tokens"),
            func.sum(UsageTransaction.output_tokens).label("total_output_tokens"),
            func.sum(UsageTransaction.audio_seconds).label("total_audio_seconds"),
            func.sum(UsageTransaction.characters).label("total_characters"),
        ).filter(
            UsageTransaction.tenant_id == tenant_id,
        )
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
                "service_type": row.service_type,
                "billing_category": row.billing_category,
                "transaction_count": row.transaction_count,
                "total_cogs": float(row.total_cogs or 0),
                "total_input_tokens": row.total_input_tokens or 0,
                "total_output_tokens": row.total_output_tokens or 0,
                "total_audio_seconds": float(row.total_audio_seconds or 0),
                "total_characters": row.total_characters or 0,
            }
            for row in rows
        ]

    def list_by_correlation(
        self,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[dict]:
        """List usage grouped by correlation_id (intent)."""
        from sqlalchemy import case, literal_column
        query = self.db.query(
            UsageTransaction.correlation_id,
            func.max(UsageTransaction.correlation_label).label("correlation_label"),
            func.count(UsageTransaction.id).label("transaction_count"),
            func.sum(UsageTransaction.cogs_amount).label("total_cogs"),
            func.min(UsageTransaction.timestamp).label("first_timestamp"),
            func.max(UsageTransaction.trigger_source).label("trigger_source"),
            func.max(UsageTransaction.tenant_id).label("tenant_id"),
            func.max(UsageTransaction.user_email).label("user_email"),
        ).filter(
            UsageTransaction.correlation_id.isnot(None),
            UsageTransaction.correlation_id != "",
        )
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)

        rows = query.group_by(
            UsageTransaction.correlation_id,
        ).order_by(
            func.min(UsageTransaction.timestamp).desc(),
        ).offset(skip).limit(limit).all()

        # Get service types per correlation_id
        result = []
        for row in rows:
            svc_types = self.db.query(
                func.distinct(UsageTransaction.service_type),
            ).filter(
                UsageTransaction.correlation_id == row.correlation_id,
            ).all()

            result.append({
                "correlation_id": row.correlation_id,
                "correlation_label": row.correlation_label,
                "transaction_count": row.transaction_count,
                "total_cogs": float(row.total_cogs or 0),
                "first_timestamp": row.first_timestamp,
                "service_types": [s[0] for s in svc_types],
                "trigger_source": row.trigger_source,
                "tenant_id": row.tenant_id,
                "user_email": row.user_email,
            })
        return result

    def count_by_correlation(
        self,
        tenant_id: Optional[str] = None,
    ) -> int:
        """Count distinct correlation groups."""
        query = self.db.query(
            func.count(func.distinct(UsageTransaction.correlation_id)),
        ).filter(
            UsageTransaction.correlation_id.isnot(None),
            UsageTransaction.correlation_id != "",
        )
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)
        return query.scalar() or 0

    def sum_cogs_by_correlation(
        self,
        tenant_id: Optional[str] = None,
    ) -> float:
        """Sum total COGS for all correlated transactions."""
        query = self.db.query(
            func.sum(UsageTransaction.cogs_amount),
        ).filter(
            UsageTransaction.correlation_id.isnot(None),
            UsageTransaction.correlation_id != "",
        )
        if tenant_id:
            query = query.filter(UsageTransaction.tenant_id == tenant_id)
        return float(query.scalar() or 0)

    def list_by_correlation_id(
        self,
        correlation_id: str,
    ) -> List[UsageTransaction]:
        """List all transactions for a single correlation_id, ordered by timestamp."""
        return self.db.query(UsageTransaction).filter(
            UsageTransaction.correlation_id == correlation_id,
        ).order_by(UsageTransaction.timestamp.asc()).all()


class CostRateCardRepository:
    """Repository for cost rate card lookups."""

    def __init__(self, db: Session):
        self.db = db

    def get_rate(
        self,
        provider: str,
        model: str,
        service_type: str,
        unit_type: str,
        as_of: Optional[date] = None,
    ) -> Optional[Decimal]:
        """Get the active rate for a provider/model/unit combination.

        Tries exact model match first, then falls back to wildcard '*'.
        Returns the rate_per_unit or None if no matching card exists.
        """
        as_of = as_of or date.today()

        # Try exact model match first
        card = self.db.query(CostRateCard).filter(
            CostRateCard.provider == provider,
            CostRateCard.model == model,
            CostRateCard.service_type == service_type,
            CostRateCard.unit_type == unit_type,
            CostRateCard.effective_from <= as_of,
            (CostRateCard.effective_to.is_(None)) | (CostRateCard.effective_to >= as_of),
        ).first()

        if card:
            return card.rate_per_unit

        # Fallback to wildcard model '*' (flat rate)
        card = self.db.query(CostRateCard).filter(
            CostRateCard.provider == provider,
            CostRateCard.model == "*",
            CostRateCard.service_type == service_type,
            CostRateCard.unit_type == unit_type,
            CostRateCard.effective_from <= as_of,
            (CostRateCard.effective_to.is_(None)) | (CostRateCard.effective_to >= as_of),
        ).first()

        return card.rate_per_unit if card else None

    def create(self, card: CostRateCard) -> CostRateCard:
        """Insert a new rate card."""
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return card

    def list_all(self, active_only: bool = True) -> List[CostRateCard]:
        """List all rate cards, optionally filtering to active only."""
        query = self.db.query(CostRateCard)
        if active_only:
            today = date.today()
            query = query.filter(
                CostRateCard.effective_from <= today,
                (CostRateCard.effective_to.is_(None)) | (CostRateCard.effective_to >= today),
            )
        return query.order_by(CostRateCard.provider, CostRateCard.model).all()
