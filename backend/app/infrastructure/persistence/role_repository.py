"""Role repository — data access layer for RBAC."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.role import Role, Permission, RolePermission, UserRole


class RoleRepository:
    """Repository for role and permission data access."""

    def __init__(self, db: Session):
        self.db = db

    # ── Permissions ──────────────────────────────────────────

    def get_or_create_permission(self, resource: str, action: str, description: str = "") -> Permission:
        """Get existing permission or create new one."""
        perm = self.db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action,
        ).first()
        if not perm:
            perm = Permission(resource=resource, action=action, description=description)
            self.db.add(perm)
            self.db.flush()
        return perm

    def list_permissions(self) -> List[Permission]:
        """List all permissions."""
        return self.db.query(Permission).order_by(Permission.resource, Permission.action).all()

    # ── Roles ────────────────────────────────────────────────

    def create_role(self, role: Role) -> Role:
        """Create a new role."""
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def get_role_by_id(self, role_id: str, tenant_id: str) -> Optional[Role]:
        """Get role by ID (tenant-scoped)."""
        return self.db.query(Role).filter(
            Role.id == role_id,
            Role.tenant_id == tenant_id,
        ).first()

    def get_role_by_name(self, name: str, tenant_id: str) -> Optional[Role]:
        """Get role by name (tenant-scoped)."""
        return self.db.query(Role).filter(
            Role.name == name,
            Role.tenant_id == tenant_id,
        ).first()

    def list_roles(self, tenant_id: str) -> List[Role]:
        """List all roles for a tenant."""
        return self.db.query(Role).filter(
            Role.tenant_id == tenant_id,
        ).order_by(Role.name).all()

    def update_role(self, role: Role) -> Role:
        """Update a role."""
        self.db.commit()
        self.db.refresh(role)
        return role

    def delete_role(self, role: Role) -> bool:
        """Delete a non-system role."""
        if role.is_system:
            return False
        self.db.delete(role)
        self.db.commit()
        return True

    # ── Role Permissions ─────────────────────────────────────

    def assign_permission_to_role(self, role_id: str, permission_id: str) -> None:
        """Assign a permission to a role."""
        existing = self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        ).first()
        if not existing:
            rp = RolePermission(role_id=role_id, permission_id=permission_id)
            self.db.add(rp)
            self.db.commit()

    def remove_permission_from_role(self, role_id: str, permission_id: str) -> None:
        """Remove a permission from a role."""
        self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        ).delete()
        self.db.commit()

    def set_role_permissions(self, role_id: str, permission_ids: List[str]) -> None:
        """Replace all permissions for a role."""
        self.db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        for pid in permission_ids:
            self.db.add(RolePermission(role_id=role_id, permission_id=pid))
        self.db.commit()

    # ── User Roles ───────────────────────────────────────────

    def assign_role_to_user(self, user_id: str, role_id: str) -> None:
        """Assign a role to a user."""
        existing = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        ).first()
        if not existing:
            ur = UserRole(user_id=user_id, role_id=role_id)
            self.db.add(ur)
            self.db.commit()

    def remove_role_from_user(self, user_id: str, role_id: str) -> None:
        """Remove a role from a user."""
        self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
        ).delete()
        self.db.commit()

    def get_user_roles(self, user_id: str) -> List[Role]:
        """Get all roles for a user."""
        user_roles = self.db.query(UserRole).filter(
            UserRole.user_id == user_id,
        ).all()
        return [ur.role for ur in user_roles]

    def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permission keys for a user (as 'resource:action' strings)."""
        roles = self.get_user_roles(user_id)
        permissions: set[str] = set()
        for role in roles:
            for perm in role.permissions:
                permissions.add(perm.key)
        return sorted(permissions)
