import os
"""CRM B4F API — business logic + aggregation, delegates CRUD to backends. Port: 8002."""
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router

settings = get_settings("crm")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

app = FastAPI( title="CRM B4F API", version="1.0.0")
setup_cors(app, "crm")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])
_api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
if _api_prefix:
    app.include_router(monitoring_router, prefix=f"/api/v1/{_api_prefix}", tags=["monitoring"])

from app.presentation.routes.contact_routes import router as contact_router
from app.presentation.routes.organization_routes import router as org_router
from app.presentation.routes.opportunity_routes import router as opp_router
from app.presentation.routes.quote_routes import router as quote_router
from app.presentation.routes.activity_routes import router as activity_router
from app.presentation.routes.product_routes import router as product_router
from app.presentation.routes.department_routes import router as dept_router
from app.presentation.routes.dashboard_routes import router as dashboard_router

app.include_router(dashboard_router, tags=["dashboard"])
app.include_router(contact_router, tags=["contacts"])
app.include_router(org_router, tags=["organizations"])
app.include_router(opp_router, tags=["opportunities"])
app.include_router(quote_router, tags=["quotes"])
app.include_router(activity_router, tags=["activities"])
app.include_router(product_router, tags=["products"])
app.include_router(dept_router, tags=["departments"])
