"""Usage Backend API — CRUD for usage transactions and cost rate cards. Port: 9011."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.event_bus import event_bus

settings = get_settings("usage-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import usage_transaction  # noqa: F401
    from app.infrastructure.database import init as db_init
    db_init("usage-backend")
    if hasattr(event_bus, 'start_listening'):
        await event_bus.start_listening()
    logger.info("usage_backend_started", port=9011)
    yield
    if hasattr(event_bus, 'close'):
        await event_bus.close()


app = FastAPI(title="Usage Backend API", version="1.0.0", lifespan=lifespan)
setup_cors(app, "usage-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.usage_routes import router as usage_router
app.include_router(usage_router, tags=["usage"])
