"""Knowledge Base API — KB Articles and Categories.

Microservice extracted from the monolith — Phase 6.
Port: 8006
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base
from app.infrastructure.database import init as db_init, get_engine

settings = get_settings("kb")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import kb_article  # noqa: F401
    db_init("kb")
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("kb_api_started", port=settings.api_port)
    yield
    logger.info("kb_api_shutdown")

app = FastAPI(title="Knowledge Base API", description="KB Articles & Categories — Croo", version="1.0.0", lifespan=lifespan)
setup_cors(app, "kb")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.kb_routes import router as kb_router
app.include_router(kb_router, tags=["knowledge-base"])
