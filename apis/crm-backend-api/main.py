"""CRM Backend API — organizations, contacts, opportunities, quotes, activities, products.

Microservice extracted from the monolith — Phase 2.
Port: 8002
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router, JWTAuthMiddleware
from shared.database import Base, create_db_engine

settings = get_settings("crm-backend")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.entities import (  # noqa: F401
        activity, contact, department, opportunity, opportunity_product,
        organization, product, quote,
    )
    engine = create_db_engine("crm-backend")
    Base.metadata.create_all(bind=engine)
    logger.info("crm_database_tables_created")
    logger.info("crm_api_started", port=settings.api_port)
    yield
    logger.info("crm_api_shutdown")


app = FastAPI(
    title="CRM Backend API",
    description="Organizations, Contacts, Opportunities, Quotes, Activities, Products — Croo Digital Experience",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app, "crm-backend")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

from app.presentation.routes.organization_routes import router as org_router
from app.presentation.routes.contact_routes import router as contact_router
from app.presentation.routes.opportunity_routes import router as opp_router
from app.presentation.routes.quote_routes import router as quote_router
from app.presentation.routes.activity_routes import router as activity_router
from app.presentation.routes.product_routes import router as product_router
from app.presentation.routes.department_routes import router as dept_router

app.include_router(org_router, tags=["organizations"])
app.include_router(contact_router, tags=["contacts"])
app.include_router(opp_router, tags=["opportunities"])
app.include_router(quote_router, tags=["quotes"])
app.include_router(activity_router, tags=["activities"])
app.include_router(product_router, tags=["products"])
app.include_router(dept_router, tags=["departments"])
