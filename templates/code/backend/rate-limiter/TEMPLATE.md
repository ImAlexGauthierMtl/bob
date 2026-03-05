# Template: Rate Limiter

> Limitation de requêtes par IP/user avec sliding window.

## Fichier à créer

`shared/infrastructure/rate_limiter.py`

```python
"""Rate limiting middleware with sliding window."""

import time
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """In-memory rate limiter (use Redis in production)."""

    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window_seconds = window_minutes * 60
        self._attempts: Dict[str, List[float]] = {}

    def _cleanup(self, key: str) -> None:
        cutoff = time.time() - self.window_seconds
        self._attempts[key] = [t for t in self._attempts.get(key, []) if t > cutoff]

    def is_limited(self, key: str) -> bool:
        self._cleanup(key)
        return len(self._attempts.get(key, [])) >= self.max_attempts

    def record(self, key: str) -> None:
        if key not in self._attempts:
            self._attempts[key] = []
        self._attempts[key].append(time.time())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)

    def remaining(self, key: str) -> int:
        self._cleanup(key)
        return max(0, self.max_attempts - len(self._attempts.get(key, [])))


# Singleton global
login_limiter = RateLimiter(max_attempts=5, window_minutes=15)


def check_rate_limit(request: Request, limiter: RateLimiter = login_limiter) -> None:
    """FastAPI dependency to check rate limit."""
    client_ip = request.client.host if request.client else "unknown"
    if limiter.is_limited(client_ip):
        logger.warning("rate_limited", ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez plus tard.",
        )
```

## Utilisation

```python
from shared.infrastructure.rate_limiter import login_limiter, check_rate_limit

@router.post("/login")
async def login(request: Request):
    check_rate_limit(request, login_limiter)
    # ... login logic
    # On failure: login_limiter.record(request.client.host)
    # On success: login_limiter.reset(request.client.host)
```
