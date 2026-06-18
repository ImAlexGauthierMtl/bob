"""Contact entity."""
import enum
from sqlalchemy import Column, String, Text, Enum as SAEnum, JSON
from app.infrastructure.persistence.models.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class ContactStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LEAD = "LEAD"


class Contact(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "contacts"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    job_title = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True)
    seniority = Column(String(50), nullable=True)
    status = Column(SAEnum(ContactStatus), default=ContactStatus.ACTIVE)
    linkedin_url = Column(String(500), nullable=True)
    headline = Column(String(500), nullable=True)
    profile_picture_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    contact_profile = Column(JSON, nullable=True)
    linkedin_followers = Column(JSON, nullable=True)
    organization_id = Column(String(36), nullable=True, index=True)
    owner_id = Column(String(36), nullable=True, index=True)
