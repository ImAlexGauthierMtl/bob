"""Observability metrics — lightweight metrics collection for monitoring.

Provides counters and histograms for key system metrics without requiring
a full Prometheus client. Exposes an endpoint for scraping.

When prometheus_client is available, uses native Prometheus metrics.
Otherwise, falls back to in-memory counters with a simple JSON endpoint.
"""

import time
from collections import defaultdict
from typing import Optional

import structlog
from fastapi import APIRouter

logger = structlog.get_logger(__name__)

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False


if HAS_PROMETHEUS:
    # Prometheus native metrics
    llm_requests_total = Counter(
        "bob_llm_requests_total",
        "Total LLM API calls",
        ["model", "trigger_source"],
    )
    llm_latency_seconds = Histogram(
        "bob_llm_latency_seconds",
        "LLM call latency",
        ["model"],
        buckets=[0.1, 0.25, 0.5, 1, 2.5, 5, 10],
    )
    provider_errors_total = Counter(
        "bob_provider_errors_total",
        "Provider API errors",
        ["provider", "service_type"],
    )
    active_voice_sessions = Gauge(
        "bob_active_voice_sessions",
        "Currently active voice sessions",
    )
    active_chat_sessions = Gauge(
        "bob_active_chat_sessions",
        "Currently active chat sessions",
    )
    rag_queries_total = Counter(
        "bob_rag_queries_total",
        "Total RAG queries",
        ["intent_category"],
    )
    rag_retrieval_chunks = Histogram(
        "bob_rag_retrieval_chunks",
        "Number of chunks retrieved per query",
        buckets=[0, 1, 3, 5, 10, 20],
    )
    enrichment_runs_total = Counter(
        "bob_enrichment_runs_total",
        "Total enrichment runs",
        ["status"],
    )
else:
    # Fallback in-memory counters
    _counters: dict[str, int] = defaultdict(int)
    _histograms: dict[str, list[float]] = defaultdict(list)

    class _FallbackCounter:
        def __init__(self, name: str):
            self.name = name

        def labels(self, **kwargs):
            key = f"{self.name}:{','.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            return _FallbackCounterInstance(key)

    class _FallbackCounterInstance:
        def __init__(self, key: str):
            self.key = key

        def inc(self, value: int = 1):
            _counters[self.key] += value

    class _FallbackHistogram:
        def __init__(self, name: str):
            self.name = name

        def labels(self, **kwargs):
            key = f"{self.name}:{','.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            return _FallbackHistogramInstance(key)

        def observe(self, value: float):
            _histograms[self.name].append(value)

    class _FallbackHistogramInstance:
        def observe(self, value: float):
            pass

    class _FallbackGauge:
        def __init__(self, name: str):
            self.name = name

        def set(self, value):
            _counters[self.name] = value

        def inc(self, value=1):
            _counters[self.name] = _counters.get(self.name, 0) + value

        def dec(self, value=1):
            _counters[self.name] = max(0, _counters.get(self.name, 0) - value)

    llm_requests_total = _FallbackCounter("bob_llm_requests_total")
    llm_latency_seconds = _FallbackHistogram("bob_llm_latency_seconds")
    provider_errors_total = _FallbackCounter("bob_provider_errors_total")
    active_voice_sessions = _FallbackGauge("bob_active_voice_sessions")
    active_chat_sessions = _FallbackGauge("bob_active_chat_sessions")
    rag_queries_total = _FallbackCounter("bob_rag_queries_total")
    rag_retrieval_chunks = _FallbackHistogram("bob_rag_retrieval_chunks")
    enrichment_runs_total = _FallbackCounter("bob_enrichment_runs_total")


# ── Convenience functions ────────────────────────────────

def record_llm_call(model: str, trigger_source: str, latency_seconds: float):
    """Record an LLM API call metric."""
    llm_requests_total.labels(model=model, trigger_source=trigger_source).inc()
    llm_latency_seconds.labels(model=model).observe(latency_seconds)


def record_provider_error(provider: str, service_type: str):
    """Record a provider API error."""
    provider_errors_total.labels(provider=provider, service_type=service_type).inc()


def record_rag_query(intent_category: str, chunks_retrieved: int):
    """Record a RAG query metric."""
    rag_queries_total.labels(intent_category=intent_category).inc()
    rag_retrieval_chunks.observe(chunks_retrieved)


def record_enrichment_run(status: str):
    """Record an enrichment run completion."""
    enrichment_runs_total.labels(status=status).inc()


# ── Metrics endpoint ─────────────────────────────────────

router = APIRouter()


@router.get("/metrics")
async def metrics_endpoint():
    """Expose metrics for Prometheus scraping or JSON fallback."""
    if HAS_PROMETHEUS:
        from fastapi.responses import Response
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse({
            "counters": dict(_counters),
            "histograms": {k: {"count": len(v), "sum": sum(v)} for k, v in _histograms.items()},
        })
