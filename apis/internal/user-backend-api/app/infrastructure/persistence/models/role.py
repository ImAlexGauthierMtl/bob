"""RBAC entities."""
from sqlalchemy import Column, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.infrastructure.persistence.models.base import Base, TenantMixin, AuditMixin, generate_uuid

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    resource = Column(String(50), nullable=False)
    action = Column(String(30), nullable=False)
    description = Column(String(255), nullable=True)
    __table_args__ = (UniqueConstraint("resource", "action", name="uq_permission_resource_action"),)
    @property
    def key(self) -> str:
        return f"{self.resource}:{self.action}"

class Role(Base, TenantMixin, AuditMixin):
    __tablename__ = "roles"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), nullable=False)
    description = Column(String(255), nullable=True)
    is_system = Column(Boolean, default=False, nullable=False)
    permissions = relationship("Permission", secondary="role_permissions", lazy="joined")
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),)

class RolePermission(Base):
    __tablename__ = "role_permissions"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

class UserRole(Base):
    __tablename__ = "user_roles"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True)
    role = relationship("Role", lazy="joined")
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)
