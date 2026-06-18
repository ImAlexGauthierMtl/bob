"""Structured logging configuration using structlog."""

from contextvars import ContextVar
import logging
import sys
import structlog
from typing import Optional

_trace_id_ctx: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
_traceparent_ctx: ContextVar[Optional[str]] = ContextVar("traceparent", default=None)
_request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Output format — 'json' for production, 'console' for dev
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "console":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Suppress noisy libraries
    for lib in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None):
    """Get a structured logger."""
    return structlog.get_logger(name)


def bind_trace_context(trace_id: str, traceparent: str, request_id: str) -> None:
    """Bind request trace context to structured logs and current context."""
    _trace_id_ctx.set(trace_id)
    _traceparent_ctx.set(traceparent)
    _request_id_ctx.set(request_id)
    structlog.contextvars.bind_contextvars(
        trace_id=trace_id,
        traceparent=traceparent,
        request_id=request_id,
    )


def clear_trace_context() -> None:
    """Clear per-request trace context."""
    _trace_id_ctx.set(None)
    _traceparent_ctx.set(None)
    _request_id_ctx.set(None)
    structlog.contextvars.unbind_contextvars("trace_id", "traceparent", "request_id")


def get_current_trace_id() -> Optional[str]:
    """Return the current request trace id, if one is bound."""
    return _trace_id_ctx.get()


def get_current_traceparent() -> Optional[str]:
    """Return the current W3C traceparent header, if one is bound."""
    return _traceparent_ctx.get()


def get_current_request_id() -> Optional[str]:
    """Return the current request id, if one is bound."""
    return _request_id_ctx.get()
