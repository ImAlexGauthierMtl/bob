"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime Opportunity route modules."""
    return (
        import_module("app.presentation.routes.opportunity_routes"),
        import_module("app.presentation.routes.quote_routes"),
    )


def load_runtime_repository_classes() -> tuple[Any, ...]:
    """Load runtime repository classes."""
    opportunities = import_module("app.infrastructure.persistence.opportunity_repository")
    quotes = import_module("app.infrastructure.persistence.quote_repository")
    return (opportunities.OpportunityRepository, quotes.QuoteRepository)


def load_runtime_entity_classes() -> tuple[Any, ...]:
    """Load runtime SQLAlchemy entity classes."""
    opportunities = import_module("app.infrastructure.persistence.models.opportunity")
    opportunity_products = import_module("app.infrastructure.persistence.models.opportunity_product")
    quotes = import_module("app.infrastructure.persistence.models.quote")
    return (
        opportunities.Opportunity,
        opportunities.OpportunityStage,
        opportunities.OpportunityPriority,
        opportunity_products.OpportunityProduct,
        quotes.Quote,
        quotes.QuoteStatus,
    )
