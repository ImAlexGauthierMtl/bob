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


class MemoryError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class MemoryForbiddenError(MemoryError):
    """Raised when a memory action is not allowed."""


class MemoryNotFoundError(MemoryError):
    """Raised when memory is missing or outside authorized scope."""
