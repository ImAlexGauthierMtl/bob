"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime Activity route modules."""
    return (import_module("app.presentation.routes.activity_routes"),)


def load_runtime_repository_classes() -> tuple[Any, ...]:
    """Load runtime repository classes."""
    module = import_module("app.infrastructure.persistence.activity_repository")
    return (module.ActivityRepository,)


def load_runtime_entity_classes() -> tuple[Any, ...]:
    """Load runtime SQLAlchemy entity classes."""
    activity = import_module("app.infrastructure.persistence.models.activity")
    return (
        activity.Activity,
        activity.ActivityType,
        activity.ActivityPriority,
        activity.ActivityStatus,
    )
