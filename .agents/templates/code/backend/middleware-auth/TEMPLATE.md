# Template: Middleware d'Authentification JWT

> Recette pour créer le middleware de vérification JWT sur les requêtes.
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`shared/infrastructure/auth_middleware.py`

## Code exact

```python
"""JWT authentication middleware."""

from typing import Callable, List, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from ..infrastructure.logging import get_logger
from ..config.settings import get_settings

logger = get_logger(__name__)
security = HTTPBearer()

_PUBLIC_PATHS: List[str] = [
    "/health",
    "/readiness",
    "/liveness",
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
    """Middleware for JWT authentication with local token verification."""

    def __init__(self, authentication_api_url: Optional[str] = None):
        self.settings = get_settings()
        self.authentication_api_url = (
            authentication_api_url
            or getattr(self.settings, "authentication_api_url", "http://authentication-api:8001")
        )

    def _is_skip_path(self, path: str) -> bool:
        """Check if the request path should bypass authentication."""
        if path in _PUBLIC_PATHS:
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
```

## Règles NON-NÉGOCIABLES

1. Paths publics TOUJOURS exemptés (health, liveness, readiness, metrics, login, register)
2. Docs/OpenAPI accessibles uniquement en dev
3. User ID et Tenant ID injectés dans `request.state`
4. Structured logging pour les erreurs de token
5. `python-jose` pour le décodage JWT
