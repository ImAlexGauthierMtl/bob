"""Milvus readiness checks with redacted outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.vector.milvus_client import (
    MilvusClientFactory,
    MilvusConfig,
    MilvusConfigError,
)

KNOWN_MILVUS_FAILURE_CODES = {
    "milvus_disabled",
    "milvus_uri_required",
    "pymilvus_not_installed",
    "vector_dimension_mismatch",
    "milvus_search_failed",
}


@dataclass(frozen=True)
class MilvusHealthStatus:
    status: str
    ready: bool
    checked: bool
    failure_code: str | None = None


class MilvusHealthCheck:
    def check(self, *, config: MilvusConfig) -> MilvusHealthStatus:
        if not config.enabled:
            return MilvusHealthStatus(status="disabled", ready=False, checked=False)
        if not config.uri:
            return MilvusHealthStatus(
                status="misconfigured",
                ready=False,
                checked=False,
                failure_code="milvus_uri_required",
            )
        try:
            client = MilvusClientFactory(config=config).create()
            client.list_collections()
        except MilvusConfigError as exc:
            return MilvusHealthStatus(
                status="unavailable",
                ready=False,
                checked=True,
                failure_code=_known_failure_code(exc),
            )
        except Exception:
            return MilvusHealthStatus(
                status="unavailable",
                ready=False,
                checked=True,
                failure_code="milvus_connection_failed",
            )
        return MilvusHealthStatus(status="ready", ready=True, checked=True)


def _known_failure_code(exc: MilvusConfigError) -> str:
    raw_code = str(exc.args[0]) if exc.args else ""
    if raw_code in KNOWN_MILVUS_FAILURE_CODES:
        return raw_code
    return "milvus_config_failed"
