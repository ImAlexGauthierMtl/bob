"""Milvus vector search adapters returning candidate IDs only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.infrastructure.vector.milvus_client import (
    MilvusClientFactory,
    MilvusConfig,
    MilvusConfigError,
)


@dataclass(frozen=True)
class VectorCandidate:
    vector_id: str
    rank: int
    distance: float | None = None


class MilvusVectorSearch:
    def search_candidates(
        self,
        *,
        config: MilvusConfig,
        collection: str,
        query_vector: list[float],
        limit: int,
    ) -> list[VectorCandidate]:
        if not config.enabled:
            raise MilvusConfigError("milvus_disabled")
        if not config.uri:
            raise MilvusConfigError("milvus_uri_required")
        if len(query_vector) != config.default_dimension:
            raise MilvusConfigError("vector_dimension_mismatch")
        try:
            client = MilvusClientFactory(config=config).create()
            result = client.search(
                collection_name=collection,
                data=[query_vector],
                limit=limit,
                output_fields=[],
            )
        except MilvusConfigError:
            raise
        except Exception as exc:
            raise MilvusConfigError("milvus_search_failed") from exc
        return _candidates_from_result(result)


def _candidates_from_result(result: Any) -> list[VectorCandidate]:
    first_page = result[0] if result else []
    candidates: list[VectorCandidate] = []
    seen: set[str] = set()
    for rank, hit in enumerate(first_page, start=1):
        vector_id = _hit_vector_id(hit)
        if not vector_id or vector_id in seen:
            continue
        seen.add(vector_id)
        candidates.append(
            VectorCandidate(
                vector_id=vector_id,
                rank=rank,
                distance=_hit_distance(hit),
            )
        )
    return candidates


def _hit_vector_id(hit: Any) -> str | None:
    if isinstance(hit, dict):
        value = hit.get("id") or hit.get("pk")
        return str(value) if value else None
    value = getattr(hit, "id", None) or getattr(hit, "pk", None)
    return str(value) if value else None


def _hit_distance(hit: Any) -> float | None:
    value = hit.get("distance") if isinstance(hit, dict) else getattr(hit, "distance", None)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
