"""Usage Backend API — CRUD + persistence for usage entities.

Pure storage layer — NO business logic.
Port: 9011
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base
from app.infrastructure.database import init as db_init, get_engine

settings = get_settings("usage-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    db_init("usage-backend")
    engine = get_engine()
    # Tables are created by the existing migrations / other APIs sharing the DB
    logger.info("usage_backend_api_started", port=settings.api_port)
    yield
    logger.info("usage_backend_api_shutdown")


app = FastAPI(
    title="Usage Backend API",
    description="Usage — CRUD + Persistence — Croo Digital Experience",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app, "usage-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

# Routes will be imported here as they are created
# from app.presentation.routes.xxx_routes import router as xxx_router
# app.include_router(xxx_router, tags=["xxx"])
