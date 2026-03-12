"""Secure RAG retriever — hybrid search with tenant/role/module isolation.

Performs:
1. Vector similarity search (if pgvector available)
2. Lexical keyword fallback (ILIKE on chunk text)
3. Strict access control filtering
4. Token budget enforcement
5. Relevance scoring and reranking
"""

from dataclasses import dataclass

import structlog
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, desc

from app.rag.models import DocumentChunk, HAS_PGVECTOR
from app.rag.embedder import embedder

logger = structlog.get_logger(__name__)

DEFAULT_TOP_K = 10
DEFAULT_MAX_CONTEXT_TOKENS = 2000


@dataclass
class RetrievalResult:
    """A single retrieved chunk with its relevance score."""
    chunk_id: str
    text: str
    source_type: str
    source_id: str
    score: float
    metadata: dict


def _build_access_filter(user_roles: list[str] | None = None, user_modules: list[str] | None = None):
    """Build SQLAlchemy filter clauses for access control."""
    filters = []

    if user_roles is not None:
        filters.append(
            or_(
                DocumentChunk.required_role.is_(None),
                DocumentChunk.required_role == "",
                DocumentChunk.required_role.in_(user_roles),
            )
        )

    if user_modules is not None:
        filters.append(
            or_(
                DocumentChunk.required_module.is_(None),
                DocumentChunk.required_module == "",
                DocumentChunk.required_module.in_(user_modules),
            )
        )

    return filters


def retrieve(
    db: Session,
    query: str,
    tenant_id: str,
    top_k: int = DEFAULT_TOP_K,
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS,
    user_roles: list[str] | None = None,
    user_modules: list[str] | None = None,
    source_types: list[str] | None = None,
) -> list[RetrievalResult]:
    """Retrieve relevant chunks with security filtering and token budgeting.

    Tries vector search first (if pgvector available), then falls back
    to lexical search. Results are filtered by tenant, role, and module.
    """
    results: list[RetrievalResult] = []

    if HAS_PGVECTOR:
        results = _vector_search(
            db, query, tenant_id, top_k,
            user_roles=user_roles,
            user_modules=user_modules,
            source_types=source_types,
        )

    if not results:
        results = _lexical_search(
            db, query, tenant_id, top_k,
            user_roles=user_roles,
            user_modules=user_modules,
            source_types=source_types,
        )

    # Token budget enforcement
    results = _enforce_token_budget(results, max_context_tokens)

    logger.info(
        "retrieval_complete",
        query_preview=query[:80],
        tenant_id=tenant_id,
        results=len(results),
        source_types=[r.source_type for r in results],
    )

    return results


def _vector_search(
    db: Session,
    query: str,
    tenant_id: str,
    top_k: int,
    user_roles: list[str] | None = None,
    user_modules: list[str] | None = None,
    source_types: list[str] | None = None,
) -> list[RetrievalResult]:
    """Perform vector similarity search using pgvector."""
    query_embedding = embedder.embed_text(query)

    base_query = (
        db.query(
            DocumentChunk,
            DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .filter(
            DocumentChunk.tenant_id == tenant_id,
            DocumentChunk.embedding.isnot(None),
        )
    )

    access_filters = _build_access_filter(user_roles, user_modules)
    for f in access_filters:
        base_query = base_query.filter(f)

    if source_types:
        base_query = base_query.filter(DocumentChunk.source_type.in_(source_types))

    rows = base_query.order_by("distance").limit(top_k).all()

    results = []
    for chunk, distance in rows:
        score = max(0.0, 1.0 - distance)
        results.append(RetrievalResult(
            chunk_id=chunk.id,
            text=chunk.text,
            source_type=chunk.source_type,
            source_id=chunk.source_id,
            score=score,
            metadata=chunk.metadata_ or {},
        ))

    return results


def _lexical_search(
    db: Session,
    query: str,
    tenant_id: str,
    top_k: int,
    user_roles: list[str] | None = None,
    user_modules: list[str] | None = None,
    source_types: list[str] | None = None,
) -> list[RetrievalResult]:
    """Fallback lexical search using ILIKE on chunk text."""
    keywords = query.strip().split()
    if not keywords:
        return []

    base_query = db.query(DocumentChunk).filter(
        DocumentChunk.tenant_id == tenant_id,
    )

    access_filters = _build_access_filter(user_roles, user_modules)
    for f in access_filters:
        base_query = base_query.filter(f)

    if source_types:
        base_query = base_query.filter(DocumentChunk.source_type.in_(source_types))

    # Match any keyword in the chunk text
    keyword_filters = [DocumentChunk.text.ilike(f"%{kw}%") for kw in keywords[:5]]
    base_query = base_query.filter(or_(*keyword_filters))

    chunks = base_query.order_by(DocumentChunk.created_at.desc()).limit(top_k).all()

    results = []
    for i, chunk in enumerate(chunks):
        # Score based on keyword match density
        text_lower = chunk.text.lower()
        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        score = matches / max(len(keywords), 1)
        results.append(RetrievalResult(
            chunk_id=chunk.id,
            text=chunk.text,
            source_type=chunk.source_type,
            source_id=chunk.source_id,
            score=score,
            metadata=chunk.metadata_ or {},
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results


def _enforce_token_budget(results: list[RetrievalResult], max_tokens: int) -> list[RetrievalResult]:
    """Trim results to fit within the token budget."""
    budgeted = []
    total_tokens = 0

    for result in results:
        tokens = len(result.text.split())
        if total_tokens + tokens > max_tokens:
            break
        budgeted.append(result)
        total_tokens += tokens

    return budgeted


def format_context(results: list[RetrievalResult]) -> str:
    """Format retrieval results into a context string for LLM injection."""
    if not results:
        return ""

    parts = ["# Retrieved Context\n"]
    for i, r in enumerate(results, 1):
        source_label = r.metadata.get("title", f"{r.source_type}/{r.source_id}")
        parts.append(f"[{i}] ({source_label})\n{r.text}\n")

    return "\n".join(parts)
