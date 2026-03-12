"""Provider resilience — retry decorator with exponential backoff.

Generic retry utility for external API calls (LLM, STT, TTS, enrichment).
"""

import asyncio
import functools
import time
from typing import Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable)


def retry_with_backoff(
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Callable | None = None,
):
    """Decorator that retries a synchronous function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay cap in seconds.
        retryable_exceptions: Tuple of exception types that trigger a retry.
        on_retry: Optional callback(attempt, exception) called before each retry.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e),
                        )
                        if on_retry:
                            on_retry(attempt + 1, e)
                        time.sleep(delay)
            raise last_exception
        return wrapper  # type: ignore
    return decorator


def async_retry_with_backoff(
    max_retries: int = 2,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Callable | None = None,
):
    """Decorator that retries an async function with exponential backoff."""
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(
                            "async_retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay=delay,
                            error=str(e),
                        )
                        if on_retry:
                            on_retry(attempt + 1, e)
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper  # type: ignore
    return decorator
