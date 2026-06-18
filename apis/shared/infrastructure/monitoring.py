"""Monitoring endpoints shared by every API."""

import os
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()

STARTED_AT = datetime.now(timezone.utc)


def _dependency_status() -> dict:
    """Return configured dependency status without doing network I/O."""
    database_configured = bool(
        os.environ.get("DATABASE_URL")
        or (
            os.environ.get("DB_HOST")
            and os.environ.get("DB_USERNAME")
            and os.environ.get("DB_DATABASE")
        )
    )
    redis_configured = bool(os.environ.get("REDIS_URL") or os.environ.get("EVENT_BUS_URL"))
    otel_configured = bool(
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get("OTLP_URL")
    )
    return {
        "database": "configured" if database_configured else "not_configured",
        "redis": "configured" if redis_configured else "not_configured",
        "otel": "configured" if otel_configured else "not_configured",
    }


def _service_name() -> str:
    return (
        os.environ.get("OTEL_SERVICE_NAME")
        or os.environ.get("API_NAME")
        or os.environ.get("HOSTNAME")
        or "unknown"
    )


@router.get("/health")
async def health():
    """Health check with dependency configuration visibility."""
    return {
        "status": "healthy",
        "service": _service_name(),
        "dependencies": _dependency_status(),
        "started_at": STARTED_AT.isoformat(),
    }


@router.get("/readiness")
async def readiness():
    """Readiness probe used by Kubernetes."""
    return {
        "status": "ready",
        "dependencies": _dependency_status(),
    }


@router.get("/liveness")
async def liveness():
    """Liveness probe confirming the process is alive."""
    return {"status": "alive", "service": _service_name()}


@router.get("/startup")
async def startup():
    """Startup probe confirming the application module loaded."""
    return {"status": "started", "started_at": STARTED_AT.isoformat()}


@router.get("/metrics")
async def metrics():
    """Minimal Prometheus text exposition without a per-service dependency."""
    service = _service_name().replace("\\", "\\\\").replace('"', '\\"')
    environment = os.environ.get("ENVIRONMENT", "development").replace("\\", "\\\\").replace('"', '\\"')
    uptime_seconds = max(0.0, (datetime.now(timezone.utc) - STARTED_AT).total_seconds())
    body = "\n".join(
        [
            "# HELP cde_api_info Static service information.",
            "# TYPE cde_api_info gauge",
            f'cde_api_info{{service="{service}",environment="{environment}"}} 1',
            "# HELP cde_api_uptime_seconds Process uptime in seconds.",
            "# TYPE cde_api_uptime_seconds gauge",
            f"cde_api_uptime_seconds {uptime_seconds:.3f}",
            "",
        ]
    )
    return Response(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
