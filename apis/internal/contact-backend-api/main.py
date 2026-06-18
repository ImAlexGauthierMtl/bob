"""Contact Backend API — CRUD for contacts. Port: 9002."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.event_bus import event_bus

settings = get_settings("contact-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import contact  # noqa: F401
    from app.infrastructure.database import init as db_init
    db_init("contact-backend")
    if hasattr(event_bus, 'start_listening'):
        await event_bus.start_listening()
    logger.info("contact_backend_started", port=9002)
    yield
    if hasattr(event_bus, 'close'):
        await event_bus.close()


app = FastAPI(title="Contact Backend API", version="1.0.0", lifespan=lifespan)
setup_cors(app, "contact-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.contact_routes import router as contact_router
app.include_router(contact_router, tags=["contacts"])
