"""Agent Memory domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


class MemoryScope:
    PRIVATE_USER = "private_user"
    ORGANIZATION = "organization"
    SHARED_CLEAN = "shared_clean"


@dataclass(frozen=True)
class InternalContext:
    tenant_id: str
    user_id: str
    trace_id: str
    permissions: tuple[str, ...] = field(default_factory=tuple)
    roles: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MemoryEntry:
    id: str
    tenant_id: str
    user_id: str
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
    expires_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class MemoryJournalEntry:
    id: str
    tenant_id: str
    user_id: str
    request_summary: str
    actions_taken: str
    sources_checked: str
    result: str
    next_step: str
    sensitivity: str
    trace_id: str
    created_at: datetime
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class VectorIndexJob:
    id: str
    tenant_id: str
    user_id: str
    collection: str
    shadow_collection: str
    scope_type: str
    status: str
    trace_id: str
    embedding_model: str
    embedding_version: str
    requested_at: datetime
    source_ref: Optional[str] = None
    dry_run: bool = False
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    rollback_of_job_id: Optional[str] = None
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class VectorIndexRecord:
    id: str
    tenant_id: str
    user_id: Optional[str]
    scope_type: str
    scope_key: str
    source_table: str
    source_id: str
    collection: str
    shadow_collection: str
    vector_id: str
    index_status: str
    content_hash: str
    embedding_model: str
    embedding_version: str
    trace_id: str
    created_at: datetime
    job_id: Optional[str] = None


@dataclass(frozen=True)
class VectorRevalidationMatch:
    vector_id: str
    source_id: str | None
    scope_type: str | None
    index_status: str | None
    accepted: bool
    rejection_code: str | None = None


@dataclass(frozen=True)
class KnowledgeDatabase:
    id: str
    tenant_id: str
    name: str
    display_name: str
    description: str
    status: str
    milvus_database: str
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    created_by: str
    created_at: datetime
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class KnowledgeCollection:
    id: str
    tenant_id: str
    database_id: str
    name: str
    display_name: str
    theme: str
    description: str
    status: str
    milvus_collection: str
    scope_type: str
    source_kind: str
    created_by: str
    created_at: datetime
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class KnowledgeSource:
    id: str
    tenant_id: str
    collection_id: str
    name: str
    provider: str
    source_type: str
    status: str
    pipedream_app: str
    pipedream_source_id: Optional[str]
    sync_mode: str
    ingestion_strategy: str
    created_by: str
    created_at: datetime
    idempotency_key: Optional[str] = None


@dataclass(frozen=True)
class KnowledgeIngestionRun:
    id: str
    tenant_id: str
    source_id: str
    trigger_type: str
    external_event_id: Optional[str]
    status: str
    raw_items_count: int
    normalized_items_count: int
    candidate_procedures_count: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    metadata_json: dict


@dataclass(frozen=True)
class KnowledgeItem:
    id: str
    tenant_id: str
    source_id: str
    run_id: Optional[str]
    external_id: str
    item_type: str
    title: str
    body: str
    metadata_json: dict
    content_hash: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class KnowledgeChunk:
    id: str
    tenant_id: str
    collection_id: str
    item_id: str
    chunk_index: int
    content: str
    content_hash: str
    metadata_json: dict
    vector_id: str
    embedding_model: str
    embedding_dimension: int
    milvus_collection: str
    status: str
    created_at: datetime
    indexed_at: Optional[datetime]


@dataclass(frozen=True)
class KnowledgeProcedure:
    id: str
    tenant_id: str
    collection_id: str
    source_item_id: Optional[str]
    title: str
    intent_key: str
    trigger_summary: str
    procedure_markdown: str
    tool_plan_json: list[dict]
    confidence: int
    status: str
    generated_by_model: str
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class MemoryError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class MemoryForbiddenError(MemoryError):
    """Raised when a memory action is not allowed."""


class MemoryNotFoundError(MemoryError):
    """Raised when memory is missing or outside authorized scope."""
