"""Capability entities — granular permission system.

Replaces simple role-based access with capability-based model:
- CapabilityDefinition: catalog of all capabilities (seed data)
- UserCapability: override per user
- DeptCapability: default for department members
"""

from sqlalchemy import Column, String, Text, Boolean, ForeignKey

from shared.database import Base, TenantMixin, AuditMixin, generate_uuid


class CapabilityDefinition(Base):
    """Catalog of available capabilities — seed data.

    Scopes: common | module | integration | automation | agent
    """

    __tablename__ = "capability_definitions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    scope = Column(String(30), nullable=False)  # common | module | integration | automation | agent
    module = Column(String(50), nullable=True)   # contacts | opportunities | quotes | etc.
    default_enabled = Column(Boolean, default=False, nullable=False)
    risk_level = Column(String(20), nullable=False, default="low")  # low | medium | high


class UserCapability(Base, TenantMixin, AuditMixin):
    """Capability override per user.

    When granted=True, the user has this capability.
    When granted=False, the capability is explicitly revoked (even if dept grants it).
    """

    __tablename__ = "user_capabilities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False, index=True, comment="Soft ref to user service users.id")
    capability_id = Column(String(36), ForeignKey("capability_definitions.id"), nullable=False, index=True)
    granted = Column(Boolean, nullable=False, default=True)
    granted_by = Column(String(100), nullable=True)


class DeptCapability(Base, TenantMixin, AuditMixin):
    """Default capability for all department members.

    Acts as the department-level default.
    Individual UserCapability can override this.
    """

    __tablename__ = "dept_capabilities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, index=True)
    capability_id = Column(String(36), ForeignKey("capability_definitions.id"), nullable=False, index=True)
    granted = Column(Boolean, nullable=False, default=True)
    granted_by = Column(String(100), nullable=True)
