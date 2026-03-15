"""Department entity."""
from sqlalchemy import Column, String, Text, ForeignKey
from app.domain.entities.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid

class Department(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "departments"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    manager_user_id = Column(String(36), nullable=True)

class UserDepartment(Base):
    __tablename__ = "user_departments"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False, index=True)
    is_manager = Column(String(5), nullable=False, default="false")
