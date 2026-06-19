"""JWT auth and permission dependencies for Agent Control B4F API."""
import os

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from shared.config import get_settings

settings = get_settings("agent-control")
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "tenant_id": payload.get("tenant_id", "default"),
        "permissions": _as_set(payload.get("permissions")),
        "capabilities": _as_set(payload.get("capabilities")),
        "roles": _as_set(payload.get("roles")) | _as_set(payload.get("platform_roles")),
    }


def require_agent_control_permission(
    current_user: dict = Depends(get_current_user),
    x_cde_capabilities: str | None = Header(None, alias="X-CDE-Capabilities"),
) -> dict:
    granted = (
        _as_set(current_user.get("permissions"))
        | _as_set(current_user.get("capabilities"))
        | _as_set(current_user.get("roles"))
        | _capabilities_from_header_or_env(x_cde_capabilities)
    )
    if "admin" in granted or "agent_control.manage" in granted or "agent_control.use" in granted:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "capability_denied", "capability": "agent_control.manage"},
    )


def _capabilities_from_header_or_env(x_cde_capabilities: str | None) -> set[str]:
    if not _is_development():
        return set()
    raw = x_cde_capabilities
    if raw is None:
        raw = os.environ.get("CDE_LOCAL_AGENT_CONTROL_CAPABILITIES")
    return _as_set(raw)


def _as_set(value) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, (list, tuple, set)):
        return {str(item).strip() for item in value if str(item).strip()}
    return {str(value).strip()} if str(value).strip() else set()


def _is_development() -> bool:
    environment = os.environ.get("ENVIRONMENT", "development").strip().lower()
    return environment in {"development", "dev", "local"}
