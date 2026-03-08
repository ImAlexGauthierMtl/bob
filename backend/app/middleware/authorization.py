"""Authorization middleware — permission and role checking dependencies."""

from typing import Sequence

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.persistence.role_repository import RoleRepository
from app.presentation.routes.auth_routes import get_current_user

import structlog

logger = structlog.get_logger(__name__)


def require_permission(*permissions: str):
    """FastAPI dependency — verify user has at least one of the required permissions.

    Usage:
        @router.get("/", dependencies=[Depends(require_permission("organization:read"))])
        async def list_organizations(...): ...

    Or in the function signature:
        async def create_org(..., _auth=Depends(require_permission("organization:write"))): ...
    """

    async def _check(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        user_perms = current_user.get("permissions", [])

        # If permissions were not pre-loaded, load them now
        if not user_perms:
            repo = RoleRepository(db)
            user_perms = repo.get_user_permissions(current_user["user_id"])
            current_user["permissions"] = user_perms

        # Check if user has at least one required permission
        has_perm = any(p in user_perms for p in permissions)

        if not has_perm:
            logger.warning(
                "authorization_denied",
                user_id=current_user["user_id"],
                required=list(permissions),
                user_permissions=user_perms,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient permissions",
                    "required": list(permissions),
                },
            )
        return current_user

    return Depends(_check)


def require_role(*roles: str):
    """FastAPI dependency — verify user has at least one of the required roles.

    Usage:
        @router.delete("/", dependencies=[Depends(require_role("admin"))])
    """

    async def _check(
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> dict:
        user_roles = current_user.get("roles", [])

        if not user_roles:
            repo = RoleRepository(db)
            role_objs = repo.get_user_roles(current_user["user_id"])
            user_roles = [r.name for r in role_objs]
            current_user["roles"] = user_roles

        has_role = any(r in user_roles for r in roles)

        if not has_role:
            logger.warning(
                "role_check_denied",
                user_id=current_user["user_id"],
                required=list(roles),
                user_roles=user_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Insufficient role",
                    "required": list(roles),
                },
            )
        return current_user

    return Depends(_check)
