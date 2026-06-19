"""Import contract for the Agent Runtime Backend API."""

from importlib import import_module

CONTRACT_VERSION = "0.1.0"


def load_runtime_components() -> tuple[object, ...]:
    return (
        import_module("main"),
        import_module("app.presentation.routes.agent_runtime_routes"),
        import_module("app.application.use_cases.agent_runtime_use_cases"),
        import_module("app.infrastructure.persistence.agent_runtime_repository"),
    )
