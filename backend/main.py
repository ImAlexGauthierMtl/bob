"""Main FastAPI application for Croo Digital Experience API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

import structlog

logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Croo Digital Experience API",
    description="Agent-First CRM/ERP — AI-powered digital experience platform",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.presentation.routes.auth_routes import router as auth_router
from app.presentation.routes.enrichment_routes import router as enrichment_router
from app.presentation.routes.organization_routes import router as organization_router

app.include_router(auth_router, tags=["auth"])
app.include_router(enrichment_router, tags=["enrichment"])
app.include_router(organization_router, tags=["organizations"])


@app.get("/health", tags=["monitoring"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "croo-digital-experience-api"}


@app.on_event("startup")
async def startup_event():
    """Startup event — create tables and seed admin user."""
    from app.infrastructure.database import engine, SessionLocal
    from app.domain.entities.base import Base
    # Import entities so they register with Base.metadata
    from app.domain.entities import user, organization  # noqa: F401
    from app.infrastructure.seed import run_seed

    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")

    # Seed admin
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()
    logger.info("api_started", environment=settings.environment)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event."""
    logger.info("api_shutdown")

