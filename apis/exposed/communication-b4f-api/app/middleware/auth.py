"""JWT auth dependency for Communication B4F API."""
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from shared.config import get_settings
from shared.services import create_service_client

settings = get_settings("communication")
security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
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
        "active_organization_id": payload.get("active_organization_id"),
    }


async def _fetch_user_profile(user_id: str, forward_headers) -> dict:
    """Fetch the authoritative user record from user~backend-api.

    Used by admin dependencies that must check flags not present in the JWT
    (e.g. `is_super_admin`, `role`).
    """
    client = create_service_client("user~backend-api")
    try:
        resp = await client.get(f"/api/v1/users/{user_id}", forward_headers=forward_headers)
        if resp.status_code != 200:
            return {}
        return resp.json() or {}
    except Exception:
        return {}


async def require_admin(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Guard a route so only tenant admins (role=admin) and super-admins can call it.

    Re-fetches the user record from user~backend-api because role / super-admin
    flags are not carried in the JWT (JWT only contains: sub, email, tenant_id,
    active_organization_id, type, exp).
    """
    user_data = await _fetch_user_profile(current_user["user_id"], request.headers)
    is_super = bool(user_data.get("is_super_admin"))
    role = (user_data.get("role") or "").lower()
    if not is_super and role not in {"admin", "super_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    # Enrich current_user for downstream handlers
    return {**current_user, "is_super_admin": is_super, "role": role}


async def require_super_admin(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Guard a route so only super-admins can call it (platform credentials etc.)."""
    user_data = await _fetch_user_profile(current_user["user_id"], request.headers)
    if not user_data.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super administrator access required")
    return {**current_user, "is_super_admin": True, "role": (user_data.get("role") or "").lower()}
