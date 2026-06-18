"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime Organization route modules."""
    return (
        import_module("app.presentation.routes.organization_routes"),
        import_module("app.presentation.routes.department_routes"),
    )


def load_runtime_repository_classes() -> tuple[Any, ...]:
    """Load runtime repository classes."""
    organizations = import_module("app.infrastructure.persistence.organization_repository")
    departments = import_module("app.infrastructure.persistence.department_repository")
    return (organizations.OrganizationRepository, departments.DepartmentRepository)


def load_runtime_entity_classes() -> tuple[Any, ...]:
    """Load runtime SQLAlchemy entity classes."""
    organizations = import_module("app.infrastructure.persistence.models.organization")
    departments = import_module("app.infrastructure.persistence.models.department")
    return (
        organizations.Organization,
        organizations.OrganizationStatus,
        organizations.OrganizationType,
        departments.Department,
        departments.UserDepartment,
    )
