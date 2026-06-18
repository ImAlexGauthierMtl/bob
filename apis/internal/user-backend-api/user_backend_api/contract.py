"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime User route modules."""
    return (
        import_module("app.presentation.routes.user_routes"),
        import_module("app.presentation.routes.tenant_routes"),
        import_module("app.presentation.routes.role_routes"),
    )


def load_runtime_repository_classes() -> tuple[Any, ...]:
    """Load runtime repository classes."""
    users = import_module("app.infrastructure.persistence.user_repository")
    tenants = import_module("app.infrastructure.persistence.tenant_repository")
    roles = import_module("app.infrastructure.persistence.role_repository")
    return (users.UserRepository, tenants.TenantRepository, roles.RoleRepository)


def load_runtime_entity_classes() -> tuple[Any, ...]:
    """Load runtime SQLAlchemy entity classes."""
    users = import_module("app.infrastructure.persistence.models.user")
    tenants = import_module("app.infrastructure.persistence.models.tenant")
    roles = import_module("app.infrastructure.persistence.models.role")
    return (
        users.User,
        tenants.Tenant,
        tenants.TenantStatus,
        tenants.TenantPlan,
        roles.Permission,
        roles.Role,
        roles.RolePermission,
        roles.UserRole,
    )
