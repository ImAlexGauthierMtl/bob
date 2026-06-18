"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> tuple[Any, ...]:
    """Load runtime Email route modules."""
    return (
        import_module("app.presentation.routes.connection_routes"),
        import_module("app.presentation.routes.email_routes"),
        import_module("app.presentation.routes.event_routes"),
        import_module("app.presentation.routes.email_contact_routes"),
        import_module("app.presentation.routes.smart_label_routes"),
        import_module("app.presentation.routes.integration_settings_routes"),
        import_module("app.presentation.routes.membrane_routes"),
        import_module("app.presentation.routes.provider_ms365_routes"),
        import_module("app.presentation.routes.provider_membrane_routes"),
    )


def load_runtime_repository_classes() -> tuple[Any, ...]:
    """Load runtime repository classes."""
    ms365 = import_module("app.infrastructure.persistence.ms365_repository")
    smart_label = import_module("app.infrastructure.persistence.smart_label_repository")
    integration = import_module("app.infrastructure.persistence.integration_settings_repository")
    membrane = import_module("app.infrastructure.persistence.membrane_repository")
    return (
        ms365.MS365Repository,
        smart_label.SmartLabelRepository,
        integration.IntegrationSettingsRepository,
        membrane.MembraneRepository,
    )


def load_runtime_entity_classes() -> tuple[Any, ...]:
    """Load runtime SQLAlchemy entity classes."""
    ms365 = import_module("app.infrastructure.persistence.models.ms365_connection")
    email = import_module("app.infrastructure.persistence.models.synced_email")
    event = import_module("app.infrastructure.persistence.models.synced_event")
    smart_label = import_module("app.infrastructure.persistence.models.smart_label")
    integration = import_module("app.infrastructure.persistence.models.integration_setting")
    membrane_conn = import_module("app.infrastructure.persistence.models.membrane_connection")
    membrane_email = import_module("app.infrastructure.persistence.models.membrane_synced_email")
    membrane_event = import_module("app.infrastructure.persistence.models.membrane_synced_event")
    return (
        ms365.MS365Connection,
        email.SyncedEmail,
        event.SyncedEvent,
        smart_label.SmartLabel,
        integration.IntegrationSetting,
        membrane_conn.MembraneConnection,
        membrane_email.MembraneSyncedEmail,
        membrane_event.MembraneSyncedEvent,
    )
