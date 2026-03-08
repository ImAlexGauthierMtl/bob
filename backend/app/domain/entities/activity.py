"""Activity entity."""

import enum

from sqlalchemy import Column, String, Text, Enum as SAEnum, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.domain.entities.base import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


class ActivityType(str, enum.Enum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    MEETING = "MEETING"
    TASK = "TASK"
    NOTE = "NOTE"


class ActivityPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class ActivityStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Activity(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Activity entity — calls, emails, meetings, tasks, notes."""

    __tablename__ = "activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Core fields
    subject = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    activity_type = Column(SAEnum(ActivityType), default=ActivityType.TASK)
    priority = Column(SAEnum(ActivityPriority), default=ActivityPriority.MEDIUM)
    status = Column(SAEnum(ActivityStatus), default=ActivityStatus.PENDING)

    # Dates
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # FK → Organization
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    organization = relationship("Organization", back_populates="activities")

    # FK → Contact
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=True, index=True)
    contact = relationship("Contact", back_populates="activities")

    # FK → Opportunity
    opportunity_id = Column(String(36), ForeignKey("opportunities.id"), nullable=True, index=True)
    opportunity = relationship("Opportunity", back_populates="activities")

    # Assigned to
    assigned_to = Column(String(100), nullable=True)

    # Owner (RBAC)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
