"""JWT auth middleware — shared across all APIs."""

from typing import Callable, List, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from .logging import get_logger
from ..config import get_settings

logger = get_logger(__name__)
security = HTTPBearer()

_PUBLIC_PATHS: List[str] = [
    "/health",
    "/readiness",
    "/liveness",
    "/startup",
    "/metrics",
    "/api/v1/login",
    "/api/v1/register",
]

_DEV_ONLY_PATHS: List[str] = [
    "/docs",
    "/openapi.json",
    "/redoc",
]


class JWTAuthMiddleware:
    """Middleware for JWT auth with local token verification.

    Validates JWT tokens and injects user_id/tenant_id into request.state.
    All microservices use this to verify tokens issued by auth-api.
    """

    def __init__(self, extra_public_paths: Optional[List[str]] = None):
        self.settings = get_settings()
        self.extra_public_paths = extra_public_paths or []

    def _is_skip_path(self, path: str) -> bool:
        """Check if the request path should bypass auth."""
        if path in _PUBLIC_PATHS or path in self.extra_public_paths:
            return True
        is_dev = self.settings.environment.lower() in ("development", "dev")
        if is_dev and path in _DEV_ONLY_PATHS:
            return True
        return False

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Validate JWT token and extract user info."""
        if self._is_skip_path(request.url.path):
            return await call_next(request)

        try:
            credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm],
            )
            request.state.user_id = payload.get("sub")
            request.state.tenant_id = payload.get("tenant_id")
        except JWTError as e:
            logger.warning("token_validation_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
