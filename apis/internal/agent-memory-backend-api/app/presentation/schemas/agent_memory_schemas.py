"""HTTP schemas for Agent Memory routes."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain import MemoryEntry, MemoryJournalEntry, VectorIndexJob, VectorRevalidationMatch


class MemoryStatusResponse(BaseModel):
    tenant_id: str
    user_id: str
    database_status: str
    memory_entries: int
    organization_entries: int
    journal_entries: int
    last_event: datetime | None = None
    isolation_enforced: bool


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    memory_types: list[str] = Field(default_factory=list)
    limit: int = Field(10, ge=1, le=50)
    include_sensitive: bool = False


class MemoryRecordRequest(BaseModel):
    memory_type: str = Field(..., min_length=1, max_length=40)
    title: str = Field(..., min_length=1, max_length=240)
    content: str = Field(..., min_length=1, max_length=12000)
    source_type: str = Field(..., min_length=1, max_length=80)
    source_ref: str = Field(..., min_length=1, max_length=512)
    sensitivity: str = Field("internal", min_length=1, max_length=40)
    verified_at: datetime
    expires_at: datetime | None = None


class MemoryEntryResponse(BaseModel):
    id: str
    scope_type: str
    memory_type: str
    title: str
    content: str
    source_type: str
    source_ref: str
    sensitivity: str
    status: str
    trace_id: str
    verified_at: datetime
    created_at: datetime
    expires_at: datetime | None = None

    @classmethod
    def from_domain(cls, entry: MemoryEntry) -> "MemoryEntryResponse":
        return cls(
            id=entry.id,
            scope_type=entry.scope_type,
            memory_type=entry.memory_type,
            title=entry.title,
            content=entry.content,
            source_type=entry.source_type,
            source_ref=entry.source_ref,
            sensitivity=entry.sensitivity,
            status=entry.status,
            trace_id=entry.trace_id,
            verified_at=entry.verified_at,
            created_at=entry.created_at,
            expires_at=entry.expires_at,
        )


class MemorySearchResponse(BaseModel):
    results: list[MemoryEntryResponse]
    isolation_enforced: bool = True
    scope_type: str


class JournalRecordRequest(BaseModel):
    request_summary: str = Field(..., min_length=1, max_length=500)
    actions_taken: str = Field(..., min_length=1, max_length=4000)
    sources_checked: str = Field(..., min_length=1, max_length=4000)
    result: str = Field(..., min_length=1, max_length=4000)
    next_step: str = Field(..., min_length=1, max_length=500)
    sensitivity: str = Field("internal", min_length=1, max_length=40)


class JournalResponse(BaseModel):
    id: str
    request_summary: str
    actions_taken: str
    sources_checked: str
    result: str
    next_step: str
    sensitivity: str
    trace_id: str
    created_at: datetime

    @classmethod
    def from_domain(cls, entry: MemoryJournalEntry) -> "JournalResponse":
        return cls(
            id=entry.id,
            request_summary=entry.request_summary,
            actions_taken=entry.actions_taken,
            sources_checked=entry.sources_checked,
            result=entry.result,
            next_step=entry.next_step,
            sensitivity=entry.sensitivity,
            trace_id=entry.trace_id,
            created_at=entry.created_at,
        )


class VectorRebuildRequest(BaseModel):
    collection: str = Field(..., min_length=1, max_length=120)
    scope_type: str | None = Field(None, min_length=1, max_length=40)
    source_ref: str | None = Field(None, max_length=512)
    dry_run: bool = False
    embedding_model: str = Field("pending-embedding-model", min_length=1, max_length=120)
    embedding_version: str = Field("v0", min_length=1, max_length=80)


class VectorPrepareRequest(BaseModel):
    limit: int = Field(500, ge=1, le=5000)


class VectorUpsertPlanRequest(BaseModel):
    limit: int = Field(500, ge=1, le=5000)


class VectorRevalidateRequest(BaseModel):
    collection: str = Field(..., min_length=1, max_length=120)
    vector_ids: list[str] = Field(..., min_length=1, max_length=100)


class RagContextRequest(BaseModel):
    collection: str = Field(..., min_length=1, max_length=120)
    vector_ids: list[str] = Field(..., min_length=1, max_length=100)
    limit: int = Field(10, ge=1, le=20)


class RagMilvusContextRequest(BaseModel):
    collection: str = Field(..., min_length=1, max_length=120)
    query_vector: list[float] = Field(..., min_length=1, max_length=4096)
    limit: int = Field(10, ge=1, le=20)


class VectorCandidateResponse(BaseModel):
    vector_id: str
    rank: int
    distance: float | None = None


class VectorIndexJobResponse(BaseModel):
    id: str
    collection: str
    shadow_collection: str
    scope_type: str
    status: str
    trace_id: str
    embedding_model: str
    embedding_version: str
    source_ref: str | None = None
    dry_run: bool
    requested_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    rollback_of_job_id: str | None = None

    @classmethod
    def from_domain(cls, job: VectorIndexJob) -> "VectorIndexJobResponse":
        return cls(
            id=job.id,
            collection=job.collection,
            shadow_collection=job.shadow_collection,
            scope_type=job.scope_type,
            status=job.status,
            trace_id=job.trace_id,
            embedding_model=job.embedding_model,
            embedding_version=job.embedding_version,
            source_ref=job.source_ref,
            dry_run=job.dry_run,
            requested_at=job.requested_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
            rollback_of_job_id=job.rollback_of_job_id,
        )


class VectorPrepareResponse(BaseModel):
    job: VectorIndexJobResponse
    planned_records: int
    stored_records: int


class VectorUpsertPlanResponse(BaseModel):
    job: VectorIndexJobResponse
    planned_records: int
    milvus_enabled: bool
    milvus_configured: bool
    embedding_provider: str
    embedding_model_configured: bool
    embedding_dimension: int
    embedding_configured: bool
    ready_for_upsert: bool


class VectorRevalidationMatchResponse(BaseModel):
    vector_id: str
    source_id: str | None
    scope_type: str | None
    index_status: str | None
    accepted: bool
    rejection_code: str | None = None

    @classmethod
    def from_domain(cls, match: VectorRevalidationMatch) -> "VectorRevalidationMatchResponse":
        return cls(
            vector_id=match.vector_id,
            source_id=match.source_id,
            scope_type=match.scope_type,
            index_status=match.index_status,
            accepted=match.accepted,
            rejection_code=match.rejection_code,
        )


class VectorRevalidateResponse(BaseModel):
    collection: str
    requested: int
    accepted: int
    rejected: int
    matches: list[VectorRevalidationMatchResponse]


class RagContextItemResponse(BaseModel):
    entry_id: str
    scope_type: str
    memory_type: str
    title: str
    content: str
    source_type: str
    source_ref: str
    sensitivity: str
    verified_at: datetime

    @classmethod
    def from_domain(cls, entry: MemoryEntry) -> "RagContextItemResponse":
        return cls(
            entry_id=entry.id,
            scope_type=entry.scope_type,
            memory_type=entry.memory_type,
            title=entry.title,
            content=entry.content,
            source_type=entry.source_type,
            source_ref=entry.source_ref,
            sensitivity=entry.sensitivity,
            verified_at=entry.verified_at,
        )


class RagContextResponse(BaseModel):
    collection: str
    trace_id: str
    audit_ref: str
    requested: int
    accepted: int
    rejected: int
    items: list[RagContextItemResponse]
    matches: list[VectorRevalidationMatchResponse]


class RagMilvusContextResponse(RagContextResponse):
    candidates: list[VectorCandidateResponse]


class VectorStoreConfigResponse(BaseModel):
    provider: str = "milvus"
    enabled: bool
    configured: bool
    uri_configured: bool
    token_configured: bool
    database: str
    secure: bool
    timeout_seconds: float
    default_dimension: int
    embedding_provider: str
    embedding_model_configured: bool
    embedding_dimension: int
    embedding_configured: bool


class VectorStoreHealthResponse(BaseModel):
    provider: str = "milvus"
    status: str
    ready: bool
    checked: bool
    enabled: bool
    configured: bool
    embedding_configured: bool
    failure_code: str | None = None
