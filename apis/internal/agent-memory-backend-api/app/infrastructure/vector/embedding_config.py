"""Embedding provider configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


class EmbeddingConfigError(RuntimeError):
    """Raised when embedding configuration is invalid."""


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    model: str
    dimension: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "EmbeddingConfig":
        source = env or os.environ
        provider = source.get("EMBEDDINGS_PROVIDER", "disabled").strip().lower() or "disabled"
        model = source.get("EMBEDDINGS_MODEL", "").strip()
        dimension = _int_env(source, "EMBEDDINGS_DIMENSION", 1536)
        if dimension <= 0:
            raise EmbeddingConfigError("embeddings_dimension_invalid")
        return cls(provider=provider, model=model, dimension=dimension)

    @property
    def configured(self) -> bool:
        return self.provider not in {"disabled", "none", "off"} and bool(self.model)

    def redacted_status(self) -> dict[str, object]:
        return {
            "embedding_provider": self.provider,
            "embedding_model_configured": bool(self.model),
            "embedding_dimension": self.dimension,
            "embedding_configured": self.configured,
        }


def _int_env(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        return int(env.get(key, str(default)))
    except ValueError as exc:
        raise EmbeddingConfigError(f"{key.lower()}_invalid") from exc
