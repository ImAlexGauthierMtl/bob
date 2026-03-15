"""Canonical backend-api template — reusable base for all ~backend-api services.

Provides:
- BaseRepository: generic CRUD with tenant isolation
- base_app_factory: creates a configured FastAPI app
- base_router: health/readiness/liveness routes
"""

from .repository import BaseRepository
from .app_factory import create_backend_app

__all__ = ["BaseRepository", "create_backend_app"]
