# Template: B4F API (Backend-for-Frontend)

> Recette pour créer une API B4F qui agrège les appels aux backend APIs.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (kebab-case) | `clients` |
| `BACKEND_API_URL` | URL du backend API | `http://clients-backend-api:8002` |

## Fichier à créer

`apis/{resource}-b4f-api/main.py`

```python
"""B4F API for {Resource} — aggregates backend API calls for the frontend."""

from fastapi import FastAPI, Request, HTTPException
from shared.config.settings import get_settings
from shared.infrastructure.logging import configure_logging, get_logger
from shared.infrastructure.middleware import setup_cors, RequestLoggingMiddleware
from shared.infrastructure.monitoring import router as monitoring_router
from shared.services.http_client import HTTPClient

settings = get_settings("{resource}-b4f")
configure_logging(settings.log_level, settings.log_format)
logger = get_logger(__name__)

app = FastAPI(title="{Resource} B4F API", version="1.0.0")
setup_cors(app, "{resource}-b4f")
app.add_middleware(RequestLoggingMiddleware)
app.include_router(monitoring_router, tags=["monitoring"])

backend_client = HTTPClient(base_url=settings.{resource}_backend_api_url or "{BACKEND_API_URL}")


def _forward_headers(request: Request) -> dict:
    """Extract and forward auth headers."""
    headers = {}
    if auth := request.headers.get("Authorization"):
        headers["Authorization"] = auth
    if tenant := request.headers.get("X-Tenant-ID"):
        headers["X-Tenant-ID"] = tenant
    return headers


@app.get("/api/v1/{resources}")
async def list_{resources}(request: Request, skip: int = 0, limit: int = 100, search: str = ""):
    """List {resources} — proxies to backend API."""
    headers = _forward_headers(request)
    response = await backend_client.get(
        f"/api/v1/{resources}?skip={skip}&limit={limit}&search={search}",
        headers=headers
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()


@app.get("/api/v1/{resources}/{{item_id}}")
async def get_{resource}(item_id: str, request: Request):
    """Get single {resource} — proxies to backend API."""
    headers = _forward_headers(request)
    response = await backend_client.get(f"/api/v1/{resources}/{item_id}", headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()


@app.post("/api/v1/{resources}")
async def create_{resource}(request: Request):
    """Create {resource} — proxies to backend API."""
    headers = _forward_headers(request)
    body = await request.json()
    response = await backend_client.post(f"/api/v1/{resources}", json=body, headers=headers)
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()


@app.put("/api/v1/{resources}/{{item_id}}")
async def update_{resource}(item_id: str, request: Request):
    """Update {resource} — proxies to backend API."""
    headers = _forward_headers(request)
    body = await request.json()
    response = await backend_client.put(f"/api/v1/{resources}/{item_id}", json=body, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()


@app.delete("/api/v1/{resources}/{{item_id}}")
async def delete_{resource}(item_id: str, request: Request):
    """Delete {resource} — proxies to backend API."""
    headers = _forward_headers(request)
    response = await backend_client.delete(f"/api/v1/{resources}/{item_id}", headers=headers)
    if response.status_code != 204:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return {"status": "deleted"}
```

## Règles NON-NÉGOCIABLES

1. B4F proxie les requêtes — pas de logique métier ici
2. Forward les headers `Authorization` et `X-Tenant-ID`
3. Utiliser `HTTPClient` du shared pour les appels
4. Status codes propagés depuis le backend
5. Le B4F peut agréger plusieurs backend APIs dans un seul endpoint
