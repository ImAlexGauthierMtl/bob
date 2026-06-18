"""Importable contract used by the shared CI template."""

from importlib import import_module
from typing import Any

OPERATIONAL_ENDPOINTS = ("/health", "/readiness", "/liveness", "/startup", "/metrics")


def load_app() -> Any:
    """Load the FastAPI app used at runtime."""
    return import_module("main").app


def load_runtime_routes() -> Any:
    """Load the runtime KB route module."""
    return import_module("app.presentation.routes.kb_routes")


def load_runtime_client_class() -> Any:
    """Load the runtime backend client class."""
    return import_module("app.infrastructure.clients.kb_client").KBClient
