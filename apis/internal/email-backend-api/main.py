"""Email Backend API — CRUD for MS365 connections, synced emails, events, contacts, smart labels.

Pure storage layer — no business logic. Port: 9007.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base
from shared.event_bus import event_bus

settings = get_settings("email-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import ms365_connection, synced_email, synced_event, email_contact, smart_label, integration_setting  # noqa: F401
    from app.infrastructure.database import init as db_init, get_engine
    db_init("email-backend")
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")

    if hasattr(event_bus, 'start_listening'):
        await event_bus.start_listening()
    logger.info("email_backend_api_started", port=settings.api_port)
    yield
    if hasattr(event_bus, 'close'):
        await event_bus.close()
    logger.info("email_backend_api_shutdown")


app = FastAPI(title="Email Backend API", version="1.0.0", lifespan=lifespan)
setup_cors(app, "email-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.connection_routes import router as connection_router
from app.presentation.routes.email_routes import router as email_router
from app.presentation.routes.event_routes import router as event_router
from app.presentation.routes.email_contact_routes import router as email_contact_router
from app.presentation.routes.smart_label_routes import router as smart_label_router
from app.presentation.routes.integration_settings_routes import router as integration_settings_router
app.include_router(connection_router, tags=["connections"])
app.include_router(email_router, tags=["emails"])
app.include_router(event_router, tags=["events"])
app.include_router(email_contact_router, tags=["email-contacts"])
app.include_router(smart_label_router, tags=["smart-labels"])
app.include_router(integration_settings_router, tags=["integration-settings"])
