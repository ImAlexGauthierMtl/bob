"""Activity entity."""

import enum

from sqlalchemy import Column, String, Text, Enum as SAEnum, DateTime, ForeignKey, Table
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


# Association tables for Many-to-Many relationships
activity_organizations = Table(
    "activity_organizations",
    Base.metadata,
    Column("activity_id", String(36), ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
    Column("organization_id", String(36), ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
)

activity_contacts = Table(
    "activity_contacts",
    Base.metadata,
    Column("activity_id", String(36), ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
    Column("contact_id", String(36), ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
)

activity_opportunities = Table(
    "activity_opportunities",
    Base.metadata,
    Column("activity_id", String(36), ForeignKey("activities.id", ondelete="CASCADE"), primary_key=True),
    Column("opportunity_id", String(36), ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True),
)


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

    # Organization Associations (M:N)
    # Kept for backward compatibility when transitioning
    organization_id = Column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    organizations = relationship(
        "Organization",
        secondary=activity_organizations,
        back_populates="linked_activities",
        lazy="selectin"
    )

    # Contact Associations (M:N)
    contact_id = Column(String(36), ForeignKey("contacts.id"), nullable=True, index=True)
    contacts = relationship(
        "Contact",
        secondary=activity_contacts,
        back_populates="linked_activities",
        lazy="selectin"
    )

    # Opportunity Associations (M:N)
    opportunity_id = Column(String(36), ForeignKey("opportunities.id"), nullable=True, index=True)
    opportunities = relationship(
        "Opportunity",
        secondary=activity_opportunities,
        back_populates="linked_activities",
        lazy="selectin"
    )

    # Assigned to
    assigned_to = Column(String(100), nullable=True)

    # Owner (RBAC)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
