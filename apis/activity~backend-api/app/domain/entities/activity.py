"""Activity entity."""
import enum
from sqlalchemy import Column, String, Text, Enum as SAEnum, DateTime, JSON
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
    __tablename__ = "activities"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    subject = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    activity_type = Column(SAEnum(ActivityType), default=ActivityType.TASK)
    priority = Column(SAEnum(ActivityPriority), default=ActivityPriority.MEDIUM)
    status = Column(SAEnum(ActivityStatus), default=ActivityStatus.PENDING)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    organization_ids = Column(JSON, nullable=True, default=list)
    contact_ids = Column(JSON, nullable=True, default=list)
    opportunity_ids = Column(JSON, nullable=True, default=list)
    assigned_to = Column(String(100), nullable=True)
    owner_id = Column(String(36), nullable=True, index=True)
