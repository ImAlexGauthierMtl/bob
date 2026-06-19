"""Milvus configuration and lazy client factory."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


class MilvusConfigError(RuntimeError):
    """Raised when Milvus is enabled but not safely configured."""


@dataclass(frozen=True)
class MilvusConfig:
    enabled: bool
    uri: str
    token: str
    database: str
    secure: bool
    timeout_seconds: float
    default_dimension: int

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "MilvusConfig":
        source = env or os.environ
        enabled = _is_enabled(source.get("MILVUS_ENABLED", "false"))
        uri = source.get("MILVUS_URI", "").strip()
        token = source.get("MILVUS_TOKEN", "").strip()
        database = source.get("MILVUS_DB_NAME", "default").strip() or "default"
        secure = _is_enabled(source.get("MILVUS_SECURE", "false"))
        timeout_seconds = _float_env(source, "MILVUS_CONNECT_TIMEOUT_SECONDS", 5.0)
        default_dimension = _int_env(source, "MILVUS_DEFAULT_DIMENSION", 1536)
        if enabled and not uri:
            raise MilvusConfigError("milvus_uri_required")
        return cls(
            enabled=enabled,
            uri=uri,
            token=token,
            database=database,
            secure=secure,
            timeout_seconds=timeout_seconds,
            default_dimension=default_dimension,
        )

    def redacted_status(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "configured": bool(self.uri),
            "uri_configured": bool(self.uri),
            "token_configured": bool(self.token),
            "database": self.database,
            "secure": self.secure,
            "timeout_seconds": self.timeout_seconds,
            "default_dimension": self.default_dimension,
        }


class MilvusClientFactory:
    def __init__(self, *, config: MilvusConfig) -> None:
        self.config = config

    def create(self):
        if not self.config.enabled:
            raise MilvusConfigError("milvus_disabled")
        if not self.config.uri:
            raise MilvusConfigError("milvus_uri_required")
        try:
            from pymilvus import MilvusClient
        except ImportError as exc:
            raise MilvusConfigError("pymilvus_not_installed") from exc
        return MilvusClient(
            uri=self.config.uri,
            token=self.config.token or None,
            db_name=self.config.database,
            timeout=self.config.timeout_seconds,
        )


def _is_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _float_env(env: Mapping[str, str], key: str, default: float) -> float:
    try:
        return float(env.get(key, str(default)))
    except ValueError as exc:
        raise MilvusConfigError(f"{key.lower()}_invalid") from exc


def _int_env(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        return int(env.get(key, str(default)))
    except ValueError as exc:
        raise MilvusConfigError(f"{key.lower()}_invalid") from exc
