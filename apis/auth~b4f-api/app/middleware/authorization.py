"""Authorization middleware — uses HTTPClient for role/permission checks."""
from fastapi import Depends, HTTPException, Request, status
from app.presentation.routes.auth_routes import get_current_user
from shared.infrastructure import get_logger

logger = get_logger(__name__)

def require_permission(*permissions: str):
    async def _check(request: Request, current_user: dict = Depends(get_current_user)) -> dict:
        user_perms = current_user.get("permissions", [])
        if not any(p in user_perms for p in permissions):
            raise HTTPException(status_code=403, detail={"error": "Insufficient permissions", "required": list(permissions)})
        return current_user
    return _check

def require_role(*roles: str):
    async def _check(request: Request, current_user: dict = Depends(get_current_user)) -> dict:
        user_roles = current_user.get("roles", [])
        if not any(r in user_roles for r in roles):
            raise HTTPException(status_code=403, detail={"error": "Insufficient role", "required": list(roles)})
        return current_user
    return _check
