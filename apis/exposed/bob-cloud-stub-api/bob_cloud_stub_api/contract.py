"""Import contract for the Bob Cloud Stub API."""

from importlib import import_module

CONTRACT_VERSION = "0.1.0"


def load_runtime_components() -> tuple[object, ...]:
    return (
        import_module("main"),
        import_module("app.presentation.routes.bob_cloud_stub_routes"),
        import_module("app.application.use_cases.bob_cloud_stub_use_cases"),
        import_module("app.infrastructure.fixtures"),
    )
