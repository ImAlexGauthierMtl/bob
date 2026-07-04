"""Agent Memory persistence models."""

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text

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


class KnowledgeDatabaseModel(Base):
    __tablename__ = "knowledge_databases"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(120), nullable=False, index=True)
    display_name = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(40), nullable=False, index=True)
    milvus_database = Column(String(120), nullable=False)
    embedding_provider = Column(String(80), nullable=False)
    embedding_model = Column(String(160), nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    created_by = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    idempotency_key = Column(String(180), nullable=True, index=True)


class KnowledgeCollectionModel(Base):
    __tablename__ = "knowledge_collections"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    database_id = Column(String(64), nullable=False, index=True)
    name = Column(String(120), nullable=False, index=True)
    display_name = Column(String(160), nullable=False)
    theme = Column(String(120), nullable=False, index=True)
    description = Column(Text, nullable=False)
    status = Column(String(40), nullable=False, index=True)
    milvus_collection = Column(String(120), nullable=False, index=True)
    scope_type = Column(String(40), nullable=False, index=True)
    source_kind = Column(String(80), nullable=False, index=True)
    created_by = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    idempotency_key = Column(String(180), nullable=True, index=True)


class KnowledgeSourceModel(Base):
    __tablename__ = "knowledge_sources"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    collection_id = Column(String(64), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    provider = Column(String(80), nullable=False, index=True)
    source_type = Column(String(80), nullable=False, index=True)
    status = Column(String(40), nullable=False, index=True)
    pipedream_app = Column(String(120), nullable=False)
    pipedream_source_id = Column(String(180), nullable=True)
    sync_mode = Column(String(80), nullable=False)
    ingestion_strategy = Column(String(80), nullable=False)
    created_by = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    idempotency_key = Column(String(180), nullable=True, index=True)


class KnowledgeIngestionRunModel(Base):
    __tablename__ = "knowledge_ingestion_runs"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    source_id = Column(String(64), nullable=False, index=True)
    trigger_type = Column(String(80), nullable=False, index=True)
    external_event_id = Column(String(180), nullable=True, index=True)
    status = Column(String(40), nullable=False, index=True)
    raw_items_count = Column(Integer, nullable=False, default=0)
    normalized_items_count = Column(Integer, nullable=False, default=0)
    candidate_procedures_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)


class KnowledgeItemModel(Base):
    __tablename__ = "knowledge_items"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    source_id = Column(String(64), nullable=False, index=True)
    run_id = Column(String(64), nullable=True, index=True)
    external_id = Column(String(180), nullable=False, index=True)
    item_type = Column(String(80), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)
    content_hash = Column(String(128), nullable=False, index=True)
    status = Column(String(40), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    collection_id = Column(String(64), nullable=False, index=True)
    item_id = Column(String(64), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(128), nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)
    vector_id = Column(String(120), nullable=False, index=True)
    embedding_model = Column(String(160), nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    milvus_collection = Column(String(120), nullable=False, index=True)
    status = Column(String(40), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    indexed_at = Column(DateTime(timezone=True), nullable=True)


class KnowledgeProcedureModel(Base):
    __tablename__ = "knowledge_procedures"
    __table_args__ = {"schema": SCHEMA_NAME}

    id = Column(String(64), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, index=True)
    collection_id = Column(String(64), nullable=False, index=True)
    source_item_id = Column(String(64), nullable=True, index=True)
    title = Column(String(240), nullable=False)
    intent_key = Column(String(160), nullable=False, index=True)
    trigger_summary = Column(Text, nullable=False)
    procedure_markdown = Column(Text, nullable=False)
    tool_plan_json = Column(JSON, nullable=False, default=list)
    confidence = Column(Integer, nullable=False)
    status = Column(String(40), nullable=False, index=True)
    generated_by_model = Column(String(160), nullable=False)
    approved_by = Column(String(64), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
