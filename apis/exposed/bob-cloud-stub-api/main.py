"""Bob Cloud local/CI contract stub.

This service mimics the Bob Cloud endpoints consumed by CDE. It is intentionally
deterministic and must never run as the production identity authority.
"""

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from shared.config import get_settings
from shared.infrastructure import (
    RequestLoggingMiddleware,
    configure_logging,
    get_logger,
    monitoring_router,
    setup_cors,
)


settings = get_settings("bob-cloud-stub")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


def assert_stub_allowed() -> None:
    mode = os.environ.get("BOB_CLOUD_MODE", "stub").lower()
    env = os.environ.get("ENV", os.environ.get("ENVIRONMENT", settings.environment)).lower()
    if mode != "stub":
        raise RuntimeError("bob-cloud-stub-api requires BOB_CLOUD_MODE=stub")
    if env in {"prod", "production"}:
        raise RuntimeError("bob-cloud-stub-api is forbidden in production")


@asynccontextmanager
async def lifespan(app: FastAPI):
    assert_stub_allowed()
    logger.info("bob_cloud_stub_started", mode=os.environ.get("BOB_CLOUD_MODE", "stub"))
    yield
    logger.info("bob_cloud_stub_shutdown")


app = FastAPI(
    title="Bob Cloud Stub API",
    description="Local/CI-only Bob Cloud contract stub",
    version="0.1.0",
    lifespan=lifespan,
)
setup_cors(app, "bob-cloud-stub")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.bob_cloud_stub_routes import router as bob_cloud_stub_router

app.include_router(bob_cloud_stub_router, tags=["bob-cloud-stub"])
