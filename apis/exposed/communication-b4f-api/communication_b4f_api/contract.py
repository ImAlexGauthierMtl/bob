"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime Communication route modules."""
    return (
        import_module("app.presentation.routes.ms365_routes"),
        import_module("app.presentation.routes.smart_label_routes"),
        import_module("app.presentation.routes.webhook_routes"),
        import_module("app.presentation.routes.membrane_routes"),
        import_module("app.presentation.routes.integration_settings_routes"),
    )


def load_runtime_client_classes() -> tuple[Any, ...]:
    """Load runtime backend client classes."""
    module = import_module("app.infrastructure.clients.email_client")
    return (
        module.IntegrationSettingsClient,
        module.ConnectionClient,
        module.EmailCrudClient,
        module.EventCrudClient,
        module.SmartLabelClient,
        module.MembraneCrudClient,
    )
