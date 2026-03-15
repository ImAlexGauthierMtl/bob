"""Communication API — MS365, Email Sync, Calendar, Smart Labels, Webhooks.

Microservice extracted from the monolith — Phase 4.
Port: 8004
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base
from app.infrastructure.database import init as db_init, get_engine

settings = get_settings("communication")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import ms365_connection, synced_email, synced_event, email_contact, smart_label  # noqa: F401
    db_init("communication")
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("communication_api_started", port=settings.api_port)
    yield
    logger.info("communication_api_shutdown")

app = FastAPI(title="Communication API", description="MS365, Emails, Calendar, Smart Labels — Croo", version="1.0.0", lifespan=lifespan)
setup_cors(app, "communication")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.ms365_routes import router as ms365_router
from app.presentation.routes.smart_label_routes import router as smart_label_router
from app.presentation.routes.webhook_routes import router as webhook_router

app.include_router(ms365_router, tags=["ms365"])
app.include_router(smart_label_router, tags=["smart-labels"])
app.include_router(webhook_router, tags=["webhooks"])
