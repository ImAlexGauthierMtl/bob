"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime Agent route modules."""
    return (
        import_module("app.presentation.routes.bcc_routes"),
        import_module("app.presentation.routes.bob_settings_routes"),
        import_module("app.presentation.routes.capability_routes"),
        import_module("app.presentation.routes.client_map_routes"),
        import_module("app.presentation.routes.training_routes"),
    )


def load_runtime_repository_classes() -> tuple[Any, ...]:
    """Load runtime repository classes."""
    module = import_module("app.infrastructure.persistence.client_map_repository")
    return (module.ClientMapRepository,)


def load_runtime_entity_classes() -> tuple[Any, ...]:
    """Load runtime SQLAlchemy entity classes."""
    bcc = import_module("app.domain.entities.bcc_entities")
    bob = import_module("app.domain.entities.bob_settings")
    capability = import_module("app.domain.entities.capability")
    client_map = import_module("app.domain.entities.client_map")
    training = import_module("app.domain.entities.training_models")
    return (
        bcc.BccOrganization,
        bcc.BccDepartment,
        bcc.BccTeam,
        bcc.BccRole,
        bob.BobUserSettings,
        capability.CapabilityDefinition,
        capability.UserCapability,
        client_map.ClientMap,
        client_map.GoldenNote,
        training.TrainingSession,
        training.TrainingNote,
        training.TrainingMissingElement,
    )
