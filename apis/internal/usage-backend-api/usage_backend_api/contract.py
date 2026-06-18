"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime Usage route modules."""
    return (import_module("app.presentation.routes.usage_routes"),)


def load_runtime_repository_classes() -> tuple[Any, ...]:
    """Load runtime repository classes."""
    module = import_module("app.infrastructure.persistence.usage_repository")
    return (module.UsageRepository,)


def load_runtime_entity_classes() -> tuple[Any, ...]:
    """Load runtime SQLAlchemy entity classes."""
    usage = import_module("app.domain.entities.usage_transaction")
    return (
        usage.UsageTransaction,
        usage.CostRateCard,
        usage.ServiceType,
        usage.BillingCategory,
        usage.TriggerSource,
        usage.RateUnitType,
    )
