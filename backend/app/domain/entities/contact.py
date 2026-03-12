"""Contact entity."""

import enum

from sqlalchemy import Column, String, Text, Enum as SAEnum, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.domain.entities.activity import activity_contacts

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
    seniority = Column(String(50), nullable=True)

    # Status
    status = Column(SAEnum(ContactStatus), default=ContactStatus.ACTIVE)

    # Social
    linkedin_url = Column(String(500), nullable=True)
    headline = Column(String(500), nullable=True, comment="LinkedIn headline")
    profile_picture_url = Column(String(500), nullable=True, comment="LinkedIn profile picture")

    # Notes
    notes = Column(Text, nullable=True)

    # AI enrichment profile (Hunter data, confidence, sources, etc.)
    contact_profile = Column(JSON, nullable=True, comment="AI enrichment data (Hunter, Compound)")

    # Bright Data LinkedIn followers
    linkedin_followers = Column(JSON, nullable=True, comment="LinkedIn followers list from Bright Data")

    # FK → Organization
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    organization = relationship("Organization", back_populates="contacts")

    # Owner (RBAC)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # Child relations
    opportunities = relationship("Opportunity", back_populates="contact", passive_deletes=True)

    # M:N with Activities
    linked_activities = relationship(
        "Activity",
        secondary=activity_contacts,
        back_populates="contacts",
        lazy="selectin"
    )
