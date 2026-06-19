"""Conversation persistence models."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text

from app.infrastructure.persistence.models.base import Base, generate_uuid, utc_now


SCHEMA_NAME = "conversation"


class ConversationSessionModel(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    channel = Column(String(50), nullable=False, default="workspace")
    status = Column(String(30), nullable=False, default="active", index=True)
    turn_count = Column(Integer, nullable=False, default=0)
    mission = Column(JSON, nullable=True)
    client_context = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class ConversationMessageModel(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    session_id = Column(
        String(64),
        ForeignKey(f"{SCHEMA_NAME}.sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    role = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
    idempotency_key = Column(String(160), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
