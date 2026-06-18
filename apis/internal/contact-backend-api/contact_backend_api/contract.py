"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime Contact route modules."""
    return (import_module("app.presentation.routes.contact_routes"),)


def load_runtime_repository_classes() -> tuple[Any, ...]:
    """Load runtime repository classes."""
    module = import_module("app.infrastructure.persistence.contact_repository")
    return (module.ContactRepository,)


def load_runtime_entity_classes() -> tuple[Any, ...]:
    """Load runtime SQLAlchemy entity classes."""
    contact = import_module("app.infrastructure.persistence.models.contact")
    return (contact.Contact, contact.ContactStatus)
