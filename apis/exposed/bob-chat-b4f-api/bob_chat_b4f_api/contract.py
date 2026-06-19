"""Import contract for the Bob Chat B4F API."""

from importlib import import_module

CONTRACT_VERSION = "0.1.0"


def load_runtime_components() -> tuple[object, ...]:
    return (
        import_module("main"),
        import_module("app.presentation.routes.bob_chat_routes"),
        import_module("app.presentation.deps"),
        import_module("app.application.use_cases.bob_chat_use_cases"),
        import_module("app.application.services.idempotency"),
        import_module("app.infrastructure.clients.conversation_client"),
        import_module("app.infrastructure.clients.agent_runtime_client"),
        import_module("app.infrastructure.clients.agent_memory_client"),
    )
