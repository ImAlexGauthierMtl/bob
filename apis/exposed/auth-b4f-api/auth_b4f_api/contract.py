"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, Any, Any, Any]:
    """Load runtime Auth route modules."""
    return (
        import_module("app.presentation.routes.auth_routes"),
        import_module("app.presentation.routes.user_routes"),
        import_module("app.presentation.routes.tenant_routes"),
        import_module("app.presentation.routes.role_routes"),
    )


def load_runtime_client_classes() -> tuple[Any, Any, Any]:
    """Load runtime backend client classes."""
    module = import_module("app.infrastructure.clients.user_client")
    return module.UserClient, module.TenantClient, module.RoleClient
