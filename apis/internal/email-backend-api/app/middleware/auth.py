"""JWT auth for backend API — validates signed claims from the B4F layer."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from shared.config import get_settings

settings = get_settings("email-backend")
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {
        "user_id": user_id,
        "email": payload.get("email"),
        "tenant_id": payload.get("tenant_id", "default"),
        "active_organization_id": payload.get("active_organization_id"),
        "role": (payload.get("role") or "").lower(),
        "is_super_admin": bool(payload.get("is_super_admin")),
    }


async def require_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Guard a route using signed admin claims, without Backend-to-Backend HTTP."""
    if not current_user["is_super_admin"] and current_user["role"] not in {"admin", "super_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def require_super_admin(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Guard a route using signed super-admin claims."""
    if not current_user["is_super_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super administrator access required")
    return current_user
