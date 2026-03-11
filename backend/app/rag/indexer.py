"""RAG Indexer — chunks, embeds, and upserts documents into the vector store.

Orchestrates the full indexing pipeline:
1. Delete existing chunks for the source
2. Split document into chunks
3. Generate embeddings
4. Persist to database
"""

import structlog
from sqlalchemy.orm import Session

from app.rag.models import DocumentChunk, HAS_PGVECTOR
from app.rag.chunker import Chunk, chunk_kb_article, chunk_bcc_profile
from app.rag.embedder import embedder

logger = structlog.get_logger(__name__)


def index_chunks(db: Session, chunks: list[Chunk], tenant_id: str) -> int:
    """Embed and persist a list of chunks. Returns count of indexed chunks."""
    if not chunks:
        return 0

    texts = [c.text for c in chunks]
    embeddings = embedder.embed_texts(texts)

    for chunk, embedding in zip(chunks, embeddings):
        doc_chunk = DocumentChunk(
            source_type=chunk.source_type,
            source_id=chunk.source_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            token_count=len(chunk.text.split()),
            visibility=chunk.metadata.get("visibility", "shared"),
            required_module=chunk.metadata.get("required_module"),
            required_role=chunk.metadata.get("required_role"),
            metadata_=chunk.metadata,
            tenant_id=tenant_id,
        )
        if HAS_PGVECTOR:
            doc_chunk.embedding = embedding
        else:
            doc_chunk.embedding_json = embedding

        db.add(doc_chunk)

    db.commit()
    logger.info("chunks_indexed", count=len(chunks), source_type=chunks[0].source_type)
    return len(chunks)


def delete_source_chunks(db: Session, source_type: str, source_id: str, tenant_id: str) -> int:
    """Remove all existing chunks for a given source."""
    count = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.source_type == source_type,
            DocumentChunk.source_id == source_id,
            DocumentChunk.tenant_id == tenant_id,
        )
        .delete()
    )
    db.commit()
    return count


def index_kb_article(
    db: Session,
    article_id: str,
    title: str,
    content: str,
    tenant_id: str,
    visibility: str = "shared",
    required_module: str | None = None,
    required_role: str | None = None,
) -> int:
    """Index a single KB article: delete old chunks, chunk, embed, persist."""
    delete_source_chunks(db, "kb_article", article_id, tenant_id)

    chunks = chunk_kb_article(
        article_id=article_id,
        title=title,
        content=content,
        tenant_id=tenant_id,
        visibility=visibility,
        required_module=required_module,
        required_role=required_role,
    )

    return index_chunks(db, chunks, tenant_id)


def index_bcc_profile_entry(
    db: Session,
    entity_type: str,
    entity_id: str,
    section: str,
    content: str,
    tenant_id: str,
) -> int:
    """Index a single BCC profile entry."""
    source_id = f"{entity_type}:{entity_id}"
    delete_source_chunks(db, "bcc_profile", source_id, tenant_id)

    chunks = chunk_bcc_profile(
        entity_type=entity_type,
        entity_id=entity_id,
        section=section,
        content=content,
        tenant_id=tenant_id,
    )

    return index_chunks(db, chunks, tenant_id)


def reindex_all_kb_articles(db: Session, tenant_id: str) -> int:
    """Re-index all published KB articles for a tenant."""
    from app.domain.entities.kb_article import KBArticle

    articles = (
        db.query(KBArticle)
        .filter(
            KBArticle.tenant_id == tenant_id,
            KBArticle.is_deleted == False,
            KBArticle.is_published == True,
        )
        .all()
    )

    total = 0
    for article in articles:
        count = index_kb_article(
            db=db,
            article_id=article.id,
            title=article.title,
            content=article.content or "",
            tenant_id=tenant_id,
            visibility=article.visibility.value if article.visibility else "shared",
            required_module=article.required_module,
            required_role=article.required_role,
        )
        total += count

    logger.info("reindex_complete", tenant_id=tenant_id, articles=len(articles), chunks=total)
    return total
