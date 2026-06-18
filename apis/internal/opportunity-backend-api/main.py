"""Opportunity Backend API — CRUD for opportunities, products, and quotes. Port: 9004."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.event_bus import event_bus

settings = get_settings("opportunity-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import opportunity, opportunity_product, quote  # noqa: F401
    from app.infrastructure.database import init as db_init
    db_init("opportunity-backend")
    if hasattr(event_bus, 'start_listening'):
        await event_bus.start_listening()
    logger.info("opportunity_backend_started", port=9004)
    yield
    if hasattr(event_bus, 'close'):
        await event_bus.close()


app = FastAPI(title="Opportunity Backend API", version="1.0.0", lifespan=lifespan)
setup_cors(app, "opportunity-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.opportunity_routes import router as opp_router
from app.presentation.routes.quote_routes import router as quote_router
app.include_router(opp_router, tags=["opportunities"])
app.include_router(quote_router, tags=["quotes"])
