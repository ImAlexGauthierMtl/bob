# Template: Monitoring & Observabilité

> Recette pour les endpoints de monitoring (health, readiness, liveness, metrics).
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`shared/infrastructure/monitoring.py`

```python
"""Monitoring endpoints: /health, /readiness, /liveness, /metrics."""

from fastapi import APIRouter
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

router = APIRouter()

# Prometheus metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method", "endpoint"],
)


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@router.get("/readiness")
async def readiness():
    """Readiness probe endpoint."""
    return {"status": "ready"}


@router.get("/liveness")
async def liveness():
    """Liveness probe endpoint."""
    return {"status": "alive"}


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

## Règles NON-NÉGOCIABLES

1. Inclure dans CHAQUE API : `app.include_router(monitoring_router, tags=["monitoring"])`
2. 3 probes K8s : `/health`, `/readiness`, `/liveness`
3. Prometheus metrics exposées sur `/metrics`
4. Pas d'authentification requise sur ces endpoints
