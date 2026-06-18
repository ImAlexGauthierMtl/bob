"""Usage application use cases."""
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, Protocol


UsageTransactionEntity = Any
RateCardEntity = Any
UsageTransactionFactory = Callable[..., UsageTransactionEntity]
RateCardFactory = Callable[..., RateCardEntity]
UsagePublisher = Callable[[str, dict[str, Any]], Awaitable[None]]


class UsageRepositoryPort(Protocol):
    def record(self, txn: UsageTransactionEntity) -> UsageTransactionEntity:
        ...

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
    ) -> list[UsageTransactionEntity]:
        ...

    def count_by_tenant(
        self,
        tenant_id: Optional[str] = None,
        service_type: Optional[str] = None,
        billing_category: Optional[str] = None,
        user_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        ...

    def get_summary(
        self,
        tenant_id: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> list[dict[str, Any]]:
        ...

    def list_by_correlation(
        self,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        ...

    def count_by_correlation(self, tenant_id: Optional[str] = None) -> int:
        ...

    def sum_cogs_by_correlation(self, tenant_id: Optional[str] = None) -> float:
        ...

    def list_by_correlation_id(self, correlation_id: str) -> list[UsageTransactionEntity]:
        ...

    def list_rate_cards(self, active_only: bool = True) -> list[RateCardEntity]:
        ...

    def create_rate_card(self, card: RateCardEntity) -> RateCardEntity:
        ...


@dataclass(frozen=True)
class UsageListResult:
    items: list[UsageTransactionEntity]
    total: int
    skip: int
    limit: int


@dataclass(frozen=True)
class UsageSummaryResult:
    tenant_id: str
    date_from: Optional[datetime]
    date_to: Optional[datetime]
    items: list[dict[str, Any]]
    total_cogs: float
    total_transactions: int


@dataclass(frozen=True)
class UsageCorrelationResult:
    items: list[dict[str, Any]]
    total: int
    skip: int
    limit: int
    total_cogs: float


class UsageUseCases:
    def __init__(
        self,
        repo: UsageRepositoryPort,
        create_usage_transaction: UsageTransactionFactory,
        create_rate_card_entity: RateCardFactory,
        publish_recorded: UsagePublisher,
    ) -> None:
        self.repo = repo
        self.create_usage_transaction = create_usage_transaction
        self.create_rate_card_entity = create_rate_card_entity
        self.publish_recorded = publish_recorded

    async def record_usage(self, data: dict[str, Any], user: dict[str, Any]) -> UsageTransactionEntity:
        txn = self.create_usage_transaction(
            tenant_id=user["tenant_id"],
            user_id=data.get("user_id") or user["user_id"],
            user_email=data.get("user_email") or user["email"],
            service_type=data["service_type"],
            provider=data.get("provider"),
            model=data.get("model"),
            is_billable=data["is_billable"],
            billing_category=data["billing_category"],
            trigger_source=data["trigger_source"],
            trigger_id=data.get("trigger_id"),
            correlation_id=data.get("correlation_id"),
            correlation_label=data.get("correlation_label"),
            input_tokens=data.get("input_tokens"),
            output_tokens=data.get("output_tokens"),
            audio_seconds=data.get("audio_seconds"),
            characters=data.get("characters"),
            voip_minutes=data.get("voip_minutes"),
            cogs_amount=data.get("cogs_amount"),
            cogs_currency=data["cogs_currency"],
            metadata_=data.get("metadata"),
            duration_ms=data.get("duration_ms"),
        )
        created = self.repo.record(txn)
        await self.publish_recorded(
            created.id,
            {"service_type": data["service_type"], "tenant_id": user["tenant_id"]},
        )
        return created

    async def list_usage(
        self,
        tenant_id: Optional[str],
        skip: int,
        limit: int,
        service_type: Optional[str],
        billing_category: Optional[str],
        user_id: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
    ) -> UsageListResult:
        filters = {
            "service_type": service_type,
            "billing_category": billing_category,
            "user_id": user_id,
            "date_from": date_from,
            "date_to": date_to,
        }
        return UsageListResult(
            items=self.repo.list_by_tenant(tenant_id, skip=skip, limit=limit, **filters),
            total=self.repo.count_by_tenant(tenant_id, **filters),
            skip=skip,
            limit=limit,
        )

    async def get_usage_summary(
        self,
        tenant_id: str,
        date_from: Optional[datetime],
        date_to: Optional[datetime],
    ) -> UsageSummaryResult:
        items = self.repo.get_summary(tenant_id, date_from=date_from, date_to=date_to)
        total_cogs = sum(row["total_cogs"] for row in items)
        total_transactions = sum(row["transaction_count"] for row in items)
        return UsageSummaryResult(
            tenant_id=tenant_id,
            date_from=date_from,
            date_to=date_to,
            items=items,
            total_cogs=round(total_cogs, 4),
            total_transactions=total_transactions,
        )

    async def list_usage_by_intent(
        self,
        tenant_id: Optional[str],
        skip: int,
        limit: int,
    ) -> UsageCorrelationResult:
        total_cogs = self.repo.sum_cogs_by_correlation(tenant_id=tenant_id)
        return UsageCorrelationResult(
            items=self.repo.list_by_correlation(tenant_id=tenant_id, skip=skip, limit=limit),
            total=self.repo.count_by_correlation(tenant_id=tenant_id),
            skip=skip,
            limit=limit,
            total_cogs=round(total_cogs, 6),
        )

    async def list_usage_by_intent_detail(self, correlation_id: str) -> UsageListResult:
        items = self.repo.list_by_correlation_id(correlation_id)
        return UsageListResult(items=items, total=len(items), skip=0, limit=len(items))

    async def list_rate_cards(self, active_only: bool) -> list[RateCardEntity]:
        return self.repo.list_rate_cards(active_only)

    async def create_rate_card(self, data: dict[str, Any]) -> RateCardEntity:
        card = self.create_rate_card_entity(
            provider=data["provider"],
            model=data["model"],
            service_type=data["service_type"],
            unit_type=data["unit_type"],
            rate_per_unit=data["rate_per_unit"],
            currency=data["currency"],
        )
        return self.repo.create_rate_card(card)
