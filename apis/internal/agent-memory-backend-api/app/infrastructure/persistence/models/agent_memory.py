"""Agent Memory persistence models."""

from sqlalchemy import Boolean, Column, DateTime, String, Text

from app.infrastructure.persistence.models.base import Base, generate_uuid, utc_now


SCHEMA_NAME = "agent_memory"


class MemoryEntryModel(Base):
    __tablename__ = "memory_entries"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    scope_type = Column(String(40), nullable=False, index=True)
    memory_type = Column(String(40), nullable=False, index=True)
    title = Column(String(240), nullable=False)
    content = Column(Text, nullable=False)
    source_type = Column(String(80), nullable=False)
    source_ref = Column(String(512), nullable=False)
    sensitivity = Column(String(40), nullable=False, index=True)
    status = Column(String(30), nullable=False, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    verified_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    idempotency_key = Column(String(180), nullable=True, index=True)


class MemoryJournalModel(Base):
    __tablename__ = "memory_journal"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    request_summary = Column(String(500), nullable=False)
    actions_taken = Column(Text, nullable=False)
    sources_checked = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    next_step = Column(String(500), nullable=False)
    sensitivity = Column(String(40), nullable=False, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    idempotency_key = Column(String(180), nullable=True, index=True)


class VectorIndexJobModel(Base):
    __tablename__ = "vector_index_jobs"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    collection = Column(String(120), nullable=False, index=True)
    shadow_collection = Column(String(180), nullable=False)
    scope_type = Column(String(40), nullable=False, index=True)
    status = Column(String(40), nullable=False, index=True)
    trace_id = Column(String(64), nullable=False, index=True)
    embedding_model = Column(String(120), nullable=False)
    embedding_version = Column(String(80), nullable=False)
    source_ref = Column(String(512), nullable=True)
    dry_run = Column(Boolean, nullable=False, default=False)
    requested_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    rollback_of_job_id = Column(String(64), nullable=True, index=True)
    idempotency_key = Column(String(180), nullable=True, index=True)


class VectorIndexRecordModel(Base):
    __tablename__ = "vector_index_records"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    scope_type = Column(String(40), nullable=False, index=True)
    scope_key = Column(String(80), nullable=True, index=True)
    source_table = Column(String(80), nullable=False)
    source_id = Column(String(64), nullable=False, index=True)
    collection = Column(String(120), nullable=False, index=True)
    shadow_collection = Column(String(180), nullable=True, index=True)
    vector_id = Column(String(120), nullable=False, index=True)
    index_status = Column(String(40), nullable=False, index=True)
    content_hash = Column(String(128), nullable=False)
    embedding_model = Column(String(120), nullable=False)
    embedding_version = Column(String(80), nullable=False)
    trace_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    job_id = Column(String(64), nullable=True, index=True)
