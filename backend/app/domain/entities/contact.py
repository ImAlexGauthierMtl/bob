"""Contact entity."""

import enum

from sqlalchemy import Column, String, Text, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from app.domain.entities.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class ContactStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LEAD = "LEAD"


class Contact(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Contact entity — people associated with organizations."""

    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Core fields
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    mobile = Column(String(50), nullable=True)
    job_title = Column(String(200), nullable=True)
    department = Column(String(100), nullable=True)

    # Status
    status = Column(SAEnum(ContactStatus), default=ContactStatus.ACTIVE)

    # Social
    linkedin_url = Column(String(500), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # FK → Organization
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    organization = relationship("Organization", backref="contacts")
