import os
"""Auth B4F API — authentication, authorization, JWT management.

B4F layer — business logic only, delegates CRUD to user~backend-api.
Port: 8001
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.config import get_settings
from shared.infrastructure import configure_logging, get_logger, setup_cors, RequestLoggingMiddleware, monitoring_router

settings = get_settings("auth")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)


async def seed_admin_user():
    """Create or update the admin user on startup."""
    from app.config import settings as auth_settings
    from app.infrastructure.clients.user_client import user_client
    from app.presentation.routes.auth_routes import create_access_token

    email = auth_settings.admin_email
    password = auth_settings.admin_password

    if not email or not password:
        logger.info("admin_seed.skipped", reason="ADMIN_EMAIL or ADMIN_PASSWORD not set")
        return

    # Retry — user-backend-api may not be ready yet
    for attempt in range(5):
        try:
            existing = await user_client.get_by_email(email)
            if existing:
                # Generate a system JWT to authenticate the update call
                system_token = create_access_token(data={
                    "sub": existing["id"],
                    "email": existing["email"],
                    "tenant_id": existing.get("tenant_id", "default"),
                })
                auth_headers = {"authorization": f"Bearer {system_token}"}

                logger.info("admin_seed.updating", email=email, user_id=existing["id"])
                await user_client.update(existing["id"], {
                    "password": password,
                    "first_name": auth_settings.admin_first_name,
                    "last_name": auth_settings.admin_last_name,
                    "is_super_admin": True,
                }, forward_headers=auth_headers)
                logger.info("admin_seed.updated", email=email)
            else:
                logger.info("admin_seed.creating", email=email)
                created = await user_client.create({
                    "email": email,
                    "password": password,
                    "first_name": auth_settings.admin_first_name,
                    "last_name": auth_settings.admin_last_name,
                    "is_super_admin": True,
                    "role": "admin",
                    "created_by": "system",
                })
                logger.info("admin_seed.created", email=email, user_id=created["id"])
            return
        except Exception as e:
            logger.warning("admin_seed.retry", attempt=attempt + 1, error=str(e))
            await asyncio.sleep(3 * (attempt + 1))

    logger.error("admin_seed.failed", reason="All retries exhausted")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_admin_user()
    yield


api_prefix = os.environ.get("API_ROUTE_PREFIX", "")
root_path = f"/api/v1/{api_prefix}" if api_prefix else ""
app = FastAPI(root_path=root_path, 
    title="Auth B4F API",
    description="Authentication & Authorization — Croo Digital Experience",
    version="1.0.0",
    lifespan=lifespan,
)

setup_cors(app, "auth")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])
if api_prefix:
    app.include_router(monitoring_router, prefix=f"/api/v1/{api_prefix}", tags=["monitoring"])

from app.presentation.routes.auth_routes import router as auth_router
from app.presentation.routes.user_routes import router as user_router
from app.presentation.routes.tenant_routes import router as tenant_router
from app.presentation.routes.role_routes import router as role_router
app.include_router(auth_router, tags=["auth"])
app.include_router(user_router, tags=["users"])
app.include_router(tenant_router, tags=["tenants"])
app.include_router(role_router, tags=["roles"])

