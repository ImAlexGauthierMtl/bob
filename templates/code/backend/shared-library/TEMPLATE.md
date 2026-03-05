# Template: Shared Library multi-API

> Package Python partagé entre toutes les APIs.

## Structure

```
apis/shared/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py          → voir config-settings/
├── database/
│   ├── __init__.py
│   ├── base.py               → Base = declarative_base()
│   └── connection.py         → voir database-config/
├── infrastructure/
│   ├── __init__.py
│   ├── logging.py            → voir middleware-cors-logging/
│   ├── middleware.py          → voir middleware-cors-logging/
│   ├── auth_middleware.py     → voir middleware-auth/
│   ├── monitoring.py          → voir monitoring-observability/
│   ├── rate_limiter.py        → voir rate-limiter/
│   └── observability.py
├── services/
│   ├── __init__.py
│   └── http_client.py        → voir http-client-service/
├── event_bus/
│   ├── __init__.py
│   └── event_bus.py           → voir event-bus/
└── utils/
    ├── __init__.py
    └── exceptions.py
```

## `shared/utils/exceptions.py`

```python
"""Custom exceptions for APIs."""

class APIError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: str = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

class NotFoundError(APIError):
    def __init__(self, resource: str, resource_id: str):
        super().__init__(f"{resource} not found: {resource_id}", status_code=404)

class ConflictError(APIError):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)
```

## Installation dans chaque API

Chaque API doit pouvoir importer `shared` :
```bash
# Dans requirements.txt de chaque API
-e ../shared    # ou bien: pip install -e ../shared
```

Ou via `PYTHONPATH` dans le Dockerfile/script :
```bash
export PYTHONPATH="${PYTHONPATH}:$(dirname $0)/.."
```
