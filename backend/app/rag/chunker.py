"""Document chunker — splits documents into indexable chunks.

Supports different strategies per document type:
- KB articles: sentence-based with overlap
- BCC profiles: section-based (one chunk per section)
- CRM entities: field-based summary chunks
"""

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 50


@dataclass
class Chunk:
    """A raw chunk before embedding."""
    text: str
    source_type: str
    source_id: str
    chunk_index: int
    metadata: dict


def chunk_by_sentences(
    text: str,
    source_type: str,
    source_id: str,
    max_tokens: int = DEFAULT_CHUNK_SIZE,
    overlap_tokens: int = DEFAULT_OVERLAP,
    metadata: dict | None = None,
) -> list[Chunk]:
    """Split text into chunks by sentence boundaries with overlap."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks = []
    current_words: list[str] = []
    current_count = 0

    for sentence in sentences:
        words = sentence.split()
        word_count = len(words)

        if current_count + word_count > max_tokens and current_words:
            chunk_text = " ".join(current_words)
            chunks.append(Chunk(
                text=chunk_text,
                source_type=source_type,
                source_id=source_id,
                chunk_index=len(chunks),
                metadata=metadata or {},
            ))
            # Keep overlap from the end of current chunk
            overlap_words = current_words[-overlap_tokens:] if overlap_tokens else []
            current_words = overlap_words + words
            current_count = len(current_words)
        else:
            current_words.extend(words)
            current_count += word_count

    if current_words:
        chunks.append(Chunk(
            text=" ".join(current_words),
            source_type=source_type,
            source_id=source_id,
            chunk_index=len(chunks),
            metadata=metadata or {},
        ))

    return chunks


def chunk_kb_article(article_id: str, title: str, content: str, tenant_id: str, **access_fields) -> list[Chunk]:
    """Chunk a KB article with title prepended to each chunk."""
    prefixed = f"{title}\n\n{content}"
    return chunk_by_sentences(
        text=prefixed,
        source_type="kb_article",
        source_id=article_id,
        metadata={
            "title": title,
            "tenant_id": tenant_id,
            **access_fields,
        },
    )


def chunk_bcc_profile(entity_type: str, entity_id: str, section: str, content: str, tenant_id: str) -> list[Chunk]:
    """Chunk a BCC profile entry — typically one chunk per section."""
    return [
        Chunk(
            text=f"[{section.capitalize()}] {content}",
            source_type="bcc_profile",
            source_id=f"{entity_type}:{entity_id}",
            chunk_index=0,
            metadata={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "section": section,
                "tenant_id": tenant_id,
            },
        )
    ]
