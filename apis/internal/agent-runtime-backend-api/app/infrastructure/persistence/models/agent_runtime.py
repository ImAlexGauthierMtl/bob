"""Agent Runtime persistence models."""

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text

from app.infrastructure.persistence.models.base import Base, generate_uuid, utc_now


SCHEMA_NAME = "agent_runtime"


class AgentRunModel(Base):
    __tablename__ = "runs"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    input_message_id = Column(String(64), nullable=False, index=True)
    status = Column(String(30), nullable=False, index=True)
    mode = Column(String(60), nullable=False)
    trace_id = Column(String(64), nullable=False, index=True)
    assistant_content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
    narration_steps = Column(JSON, nullable=False, default=list)
    actions = Column(JSON, nullable=False, default=list)
    artifacts = Column(JSON, nullable=False, default=list)
    idempotency_key = Column(String(180), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)


class AgentConfirmationModel(Base):
    __tablename__ = "confirmations"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    run_id = Column(
        String(64),
        ForeignKey(f"{SCHEMA_NAME}.runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    status = Column(String(30), nullable=False, index=True)
    label = Column(String(160), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class RuntimeCatalogItemModel(Base):
    __tablename__ = "runtime_catalog_items"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    collection = Column(String(30), nullable=False, index=True)
    name = Column(String(180), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    payload_hash = Column(String(64), nullable=False)
    idempotency_key = Column(String(180), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
