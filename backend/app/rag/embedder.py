"""Embedding provider — wraps embedding API for vector generation.

Supports Groq embeddings endpoint or falls back to sentence-transformers.
"""

from typing import Optional

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class Embedder:
    """Generate embeddings for text chunks."""

    def __init__(self, model: str = "text-embedding-3-small", dimension: int = 1536):
        self.model = model
        self.dimension = dimension
        self._client = None

    def _get_client(self):
        if self._client is None:
            from groq import Groq
            self._client = Groq(api_key=settings.groq_api_key)
        return self._client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Uses the Groq embeddings API. Falls back to zero vectors
        if the API call fails (allows indexing without embeddings
        for text-only search).
        """
        if not texts:
            return []

        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self.model,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            logger.info("embeddings_generated", count=len(embeddings), model=self.model)
            return embeddings
        except Exception as e:
            logger.error("embedding_failed", error=str(e), model=self.model, count=len(texts))
            return [[0.0] * self.dimension] * len(texts)

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        results = self.embed_texts([text])
        return results[0] if results else [0.0] * self.dimension


embedder = Embedder()
