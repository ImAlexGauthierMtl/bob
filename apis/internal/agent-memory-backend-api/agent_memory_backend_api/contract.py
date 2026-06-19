"""Import contract for Agent Memory Backend."""

from importlib import import_module

CONTRACT_VERSION = "0.1.0"


def load_memory_components() -> tuple[object, ...]:
    return (
        import_module("app.domain.entities"),
        import_module("app.application.use_cases.agent_memory_use_cases"),
        import_module("app.infrastructure.persistence.agent_memory_repository"),
        import_module("app.infrastructure.vector.embedding_config"),
        import_module("app.infrastructure.vector.milvus_client"),
        import_module("app.presentation.routes.agent_memory_routes"),
    )
