"""Training models — track sessions, notes, and missing elements.

Stores training progress per user, notes captured during voice training
with Bob, and missing elements (features, integrations) identified.
"""

import uuid

from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, func
from shared.database import Base, TenantMixin


def _uuid() -> str:
    return str(uuid.uuid4())


class TrainingSession(Base, TenantMixin):
    """A user's training session for a specific course."""

    __tablename__ = "training_sessions"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    training_slug = Column(String(100), nullable=False, index=True)
    current_slide = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class TrainingNote(Base, TenantMixin):
    """A note captured during training (by Bob or manually)."""

    __tablename__ = "training_notes"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("training_sessions.id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    slide_id = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    note_type = Column(String(20), default="insight", nullable=False)  # insight | action | important
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TrainingMissingElement(Base, TenantMixin):
    """A missing feature/integration identified during training."""

    __tablename__ = "training_missing_elements"

    id = Column(String(36), primary_key=True, default=_uuid)
    session_id = Column(String(36), ForeignKey("training_sessions.id"), nullable=False, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    label = Column(String(200), nullable=False)
    category = Column(String(50), default="integration", nullable=False)  # integration | feature | process
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
