"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime AI Agent route modules."""
    return (
        import_module("app.presentation.routes.bcc_routes"),
        import_module("app.presentation.routes.bob_settings_routes"),
        import_module("app.presentation.routes.bob_chat_routes"),
        import_module("app.presentation.routes.client_map_routes"),
        import_module("app.presentation.routes.capability_routes"),
        import_module("app.presentation.routes.training_routes"),
    )


def load_runtime_client_classes() -> tuple[Any, ...]:
    """Load runtime backend client classes."""
    module = import_module("app.infrastructure.clients.agent_client")
    return (
        module.BccClient,
        module.BobSettingsClient,
        module.ClientMapClient,
        module.CapabilityClient,
        module.TrainingClient,
    )
