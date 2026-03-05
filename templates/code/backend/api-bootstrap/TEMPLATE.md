# Template: Bootstrap API FastAPI

> Recette pour initialiser une nouvelle API FastAPI avec toute l'infrastructure.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `API_NAME` | Nom de l'API (kebab-case) | `clients-backend-api` |
| `API_TITLE` | Titre de l'API | `Clients Backend API` |
| `API_DESC` | Description courte | `Backend service for clients management` |
| `PORT` | Port par défaut | `8002` |

## Fichiers à créer

```
{API_NAME}/
├── main.py
├── requirements.txt
├── Dockerfile
├── run_api.sh
├── run_tests.sh
├── migrate.sh
├── pytest.ini
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── domain/
│   │   ├── __init__.py
│   │   └── entities/
│   ├── application/
│   │   ├── __init__.py
│   │   └── use_cases/
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── persistence/
│   └── presentation/
│       ├── __init__.py
│       ├── routes/
│       └── schemas/
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   ├── __init__.py
    │   └── database.py
    ├── unit/
    │   └── __init__.py
    └── integration/
        └── __init__.py
```

## 1. `main.py` — Point d'entrée

```python
"""Main FastAPI application for {API_TITLE}."""

from fastapi import FastAPI
from shared.config.settings import get_settings
from shared.infrastructure.logging import configure_logging, get_logger
from shared.infrastructure.middleware import setup_cors, RequestLoggingMiddleware, ErrorHandlingMiddleware
from shared.infrastructure.monitoring import router as monitoring_router
from shared.infrastructure.observability import configure_observability
# from app.presentation.routes.{resources} import router as {resources}_router

# Configure logging
settings = get_settings("{api_name}")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

# Configure observability
configure_observability("{api_name}")

# Create FastAPI app
app = FastAPI(
    title="{API_TITLE}",
    description="{API_DESC}",
    version="1.0.0",
)

# Instrument FastAPI for automatic tracing
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
except ImportError:
    pass  # OpenTelemetry instrumentation not available

# Setup middleware
setup_cors(app, "{api_name}")
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ErrorHandlingMiddleware)

# Include routers
app.include_router(monitoring_router, tags=["monitoring"])
# app.include_router({resources}_router, prefix="/api/v1", tags=["{resources}"])


@app.on_event("startup")
async def startup_event():
    """Startup event."""
    logger.info("{api_name_snake}_started", environment=settings.environment, port=settings.api_port)


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event."""
    logger.info("{api_name_snake}_shutdown")
```

## 2. `requirements.txt`

```text
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0
alembic>=1.13
pydantic>=2.0
pydantic-settings>=2.0
python-jose[cryptography]>=3.3
bcrypt>=4.0
httpx>=0.27
structlog>=24.0
prometheus-client>=0.19
opentelemetry-api>=1.20
opentelemetry-sdk>=1.20
opentelemetry-instrumentation-fastapi>=0.41
pytest>=8.0
pytest-asyncio>=0.23
```

## 3. `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

ENV PIP_DEFAULT_TIMEOUT=300

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE {PORT}

# Run the application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-{PORT}}"]
```

## 4. `run_api.sh`

```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
uvicorn main:app --reload --host 0.0.0.0 --port ${PORT:-{PORT}}
```

## 5. `run_tests.sh`

```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || true
python -m pytest tests/ -v --tb=short
```

## 6. `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto
```

## Règles NON-NÉGOCIABLES

1. Toujours utiliser la `shared` library pour config, logging, middleware, monitoring
2. CORS configuré via `setup_cors()` avec le nom de l'API
3. Middleware de logging et error handling TOUJOURS ajoutés
4. Health/readiness/liveness endpoints via `monitoring_router`
5. Structured logging — jamais `print()`, jamais `logging.basicConfig()` direct
6. OpenTelemetry instrumentation optionnelle (try/except ImportError)
7. Préfixe `/api/v1` sur tous les routers métier

## Après création

1. Configurer les variables d'environnement dans `.env`
2. Créer le venv : `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
3. Ajouter les modèles → voir `templates/code/backend/domain-entity/`
4. Ajouter le service dans `docker-compose.yml`
