"""Activity Backend API — CRUD for activities. Port: 9005."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.database import Base
from shared.event_bus import event_bus

settings = get_settings("activity-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import activity  # noqa: F401
    from app.infrastructure.database import init as db_init, get_engine
    db_init("activity-backend")
    Base.metadata.create_all(bind=get_engine())
    if hasattr(event_bus, 'start_listening'):
        await event_bus.start_listening()
    logger.info("activity_backend_started", port=9005)
    yield
    if hasattr(event_bus, 'close'):
        await event_bus.close()


app = FastAPI(title="Activity Backend API", version="1.0.0", lifespan=lifespan)
setup_cors(app, "activity-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.activity_routes import router as activity_router
app.include_router(activity_router, tags=["activities"])
