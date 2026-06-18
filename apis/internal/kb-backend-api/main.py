"""KB Backend API — CRUD for knowledge base articles and categories. Port: 9010."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router
from shared.event_bus import event_bus

settings = get_settings("kb-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import kb_article  # noqa: F401
    from app.infrastructure.database import init as db_init
    db_init("kb-backend")
    if hasattr(event_bus, 'start_listening'):
        await event_bus.start_listening()
    logger.info("kb_backend_started", port=9010)
    yield
    if hasattr(event_bus, 'close'):
        await event_bus.close()


app = FastAPI(title="KB Backend API", version="1.0.0", lifespan=lifespan)
setup_cors(app, "kb-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.kb_routes import router as kb_router
app.include_router(kb_router, tags=["knowledge-base"])
