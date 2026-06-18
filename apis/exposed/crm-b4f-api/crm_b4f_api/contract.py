"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime CRM route modules."""
    return (
        import_module("app.presentation.routes.contact_routes"),
        import_module("app.presentation.routes.organization_routes"),
        import_module("app.presentation.routes.opportunity_routes"),
        import_module("app.presentation.routes.quote_routes"),
        import_module("app.presentation.routes.activity_routes"),
        import_module("app.presentation.routes.product_routes"),
        import_module("app.presentation.routes.department_routes"),
    )


def load_runtime_client_classes() -> tuple[Any, ...]:
    """Load runtime backend client classes."""
    module = import_module("app.infrastructure.clients.crm_clients")
    return (
        module.ContactClient,
        module.OrgClient,
        module.OpportunityClient,
        module.ActivityClient,
        module.ProductClient,
    )
