"""Presentation dependencies for Usage API."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.use_cases.usage_use_cases import UsageUseCases
from app.events.publishers import publish_usage_recorded
from app.infrastructure.database import get_db
from app.infrastructure.persistence.models.usage_transaction import CostRateCard, UsageTransaction
from app.infrastructure.persistence.usage_repository import UsageRepository


def get_usage_use_cases(db: Session = Depends(get_db)) -> UsageUseCases:
    return UsageUseCases(
        repo=UsageRepository(db),
        create_usage_transaction=UsageTransaction,
        create_rate_card_entity=CostRateCard,
        publish_recorded=publish_usage_recorded,
    )
