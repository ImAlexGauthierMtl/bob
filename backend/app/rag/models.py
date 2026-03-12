"""RAG data models — DocumentChunk for vector store indexing."""

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Index
from sqlalchemy.orm import Session

from app.domain.entities.base import Base, TenantMixin, AuditMixin, generate_uuid, utc_now

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class DocumentChunk(Base, TenantMixin, AuditMixin):
    """A single chunk of a document, stored with its embedding for vector search."""

    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # Source tracking
    source_type = Column(String(50), nullable=False, index=True)
    source_id = Column(String(36), nullable=False, index=True)
    chunk_index = Column(Integer, default=0)

    # Content
    text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)

    # Embedding (pgvector column if available, else stored as JSON)
    if HAS_PGVECTOR:
        embedding = Column(Vector(1536), nullable=True)
    else:
        embedding_json = Column(JSON, nullable=True)

    # Access control (mirroring the source document's permissions)
    visibility = Column(String(20), default="shared")
    required_module = Column(String(100), nullable=True)
    required_role = Column(String(50), nullable=True)

    # Metadata
    metadata_ = Column("metadata", JSON, nullable=True, default=dict)

    __table_args__ = (
        Index("ix_chunk_source", "source_type", "source_id"),
        Index("ix_chunk_tenant_source", "tenant_id", "source_type"),
    )


# Source type constants
SOURCE_KB_ARTICLE = "kb_article"
SOURCE_BCC_PROFILE = "bcc_profile"
SOURCE_CRM_ENTITY = "crm_entity"
