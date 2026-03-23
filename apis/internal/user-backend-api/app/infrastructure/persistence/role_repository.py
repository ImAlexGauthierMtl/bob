"""Role repository — data access layer for RBAC."""

from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.entities.role import Role, Permission, RolePermission, UserRole


class RoleRepository:
    """Repository for role and permission data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_permission(self, resource: str, action: str, description: str = "") -> Permission:
        perm = self.db.query(Permission).filter(
            Permission.resource == resource, Permission.action == action,
        ).first()
        if not perm:
            perm = Permission(resource=resource, action=action, description=description)
            self.db.add(perm)
            self.db.flush()
        return perm

    def list_permissions(self) -> List[Permission]:
        return self.db.query(Permission).order_by(Permission.resource, Permission.action).all()

    def create_role(self, role: Role) -> Role:
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def get_role_by_id(self, role_id: str, tenant_id: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.id == role_id, Role.tenant_id == tenant_id).first()

    def get_role_by_name(self, name: str, tenant_id: str) -> Optional[Role]:
        return self.db.query(Role).filter(Role.name == name, Role.tenant_id == tenant_id).first()

    def list_roles(self, tenant_id: str) -> List[Role]:
        return self.db.query(Role).filter(Role.tenant_id == tenant_id).order_by(Role.name).all()

    def update_role(self, role: Role) -> Role:
        self.db.commit()
        self.db.refresh(role)
        return role

    def delete_role(self, role: Role) -> bool:
        if role.is_system:
            return False
        self.db.delete(role)
        self.db.commit()
        return True

    def assign_permission_to_role(self, role_id: str, permission_id: str) -> None:
        existing = self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id, RolePermission.permission_id == permission_id,
        ).first()
        if not existing:
            self.db.add(RolePermission(role_id=role_id, permission_id=permission_id))
            self.db.commit()

    def remove_permission_from_role(self, role_id: str, permission_id: str) -> None:
        self.db.query(RolePermission).filter(
            RolePermission.role_id == role_id, RolePermission.permission_id == permission_id,
        ).delete()
        self.db.commit()

    def set_role_permissions(self, role_id: str, permission_ids: List[str]) -> None:
        self.db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        for pid in permission_ids:
            self.db.add(RolePermission(role_id=role_id, permission_id=pid))
        self.db.commit()

    def assign_role_to_user(self, user_id: str, role_id: str) -> None:
        existing = self.db.query(UserRole).filter(
            UserRole.user_id == user_id, UserRole.role_id == role_id,
        ).first()
        if not existing:
            self.db.add(UserRole(user_id=user_id, role_id=role_id))
            self.db.commit()

    def remove_role_from_user(self, user_id: str, role_id: str) -> None:
        self.db.query(UserRole).filter(
            UserRole.user_id == user_id, UserRole.role_id == role_id,
        ).delete()
        self.db.commit()

    def get_user_roles(self, user_id: str) -> List[Role]:
        user_roles = self.db.query(UserRole).filter(UserRole.user_id == user_id).all()
        return [ur.role for ur in user_roles]

    def get_user_permissions(self, user_id: str) -> List[str]:
        roles = self.get_user_roles(user_id)
        permissions: set[str] = set()
        for role in roles:
            for perm in role.permissions:
                permissions.add(perm.key)
        return sorted(permissions)
