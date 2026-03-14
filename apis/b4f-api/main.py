"""B4F API (Backend-for-Frontend) — Single gateway for the Angular frontend.

Proxies all requests to the appropriate backend microservice.
The frontend talks ONLY to this service on port 8000.
"""

import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(
    title="Croo B4F API",
    description="Backend-for-Frontend — gateway aggregating all microservices",
    version="1.0.0",
)

# ── CORS ─────────────────────────────────────────────────────
origins = os.getenv("CORS_ORIGINS", '["http://localhost:4200","http://localhost:4700"]')
import json
try:
    cors_list = json.loads(origins)
except Exception:
    cors_list = ["http://localhost:4200", "http://localhost:4700"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Backend URLs ─────────────────────────────────────────────
BACKENDS = {
    "auth":               os.getenv("AUTH_API_URL", "http://auth-api:8001"),
    "crm":                os.getenv("CRM_API_URL", "http://crm-backend-api:8002"),
    "ai-agent":           os.getenv("AI_AGENT_API_URL", "http://ai-agent-api:8003"),
    "communication":      os.getenv("COMMUNICATION_API_URL", "http://communication-api:8004"),
    "platform-services":  os.getenv("PLATFORM_SERVICES_API_URL", "http://platform-services-api:8005"),
    "kb":                 os.getenv("KB_API_URL", "http://kb-api:8006"),
    "legacy":             os.getenv("LEGACY_API_URL", "http://api:4500"),
}

# ── Route → Backend mapping ──────────────────────────────────
ROUTE_MAP = [
    # Auth
    ("/api/v1/auth",       "auth"),
    ("/api/v1/users",      "auth"),
    ("/api/v1/tenants",    "auth"),
    ("/api/v1/roles",      "auth"),
    # CRM
    ("/api/v1/organizations", "crm"),
    ("/api/v1/contacts",      "crm"),
    ("/api/v1/opportunities", "crm"),
    ("/api/v1/quotes",        "crm"),
    ("/api/v1/activities",    "crm"),
    ("/api/v1/products",      "crm"),
    ("/api/v1/departments",   "crm"),
    # AI Agent
    ("/api/v1/bcc",           "ai-agent"),
    ("/api/v1/bob",           "ai-agent"),
    ("/api/v1/capabilities",  "ai-agent"),
    ("/api/v1/training",      "ai-agent"),
    ("/api/v1/client-map",    "ai-agent"),
    # Communication
    ("/api/v1/ms365",         "communication"),
    ("/api/v1/smart-labels",  "communication"),
    ("/api/v1/webhooks",      "communication"),
    # Platform Services
    ("/api/v1/workflows",     "platform-services"),
    ("/api/v1/usage",         "platform-services"),
    ("/api/v1/enrichment",    "platform-services"),
    # Knowledge Base
    ("/api/v1/kb",            "kb"),
]


def _resolve_backend(path: str) -> str | None:
    """Find which backend should handle this path."""
    for prefix, backend_key in ROUTE_MAP:
        if path.startswith(prefix):
            return BACKENDS[backend_key]
    return None


def _forward_headers(request: Request) -> dict:
    """Extract and forward auth + tenant headers."""
    headers = {}
    if auth := request.headers.get("authorization"):
        headers["Authorization"] = auth
    if tenant := request.headers.get("x-tenant-id"):
        headers["X-Tenant-ID"] = tenant
    if ct := request.headers.get("content-type"):
        headers["Content-Type"] = ct
    return headers


# ── Health ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "b4f-api"}


# ── Catch-all proxy ─────────────────────────────────────────
@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(request: Request, path: str):
    """Proxy all /api/* requests to the appropriate backend."""
    full_path = f"/api/{path}"
    backend_url = _resolve_backend(full_path)

    if not backend_url:
        # Fallback to legacy monolith
        backend_url = BACKENDS["legacy"]

    target_url = f"{backend_url}{full_path}"

    # Forward query params
    if request.url.query:
        target_url += f"?{request.url.query}"

    headers = _forward_headers(request)

    # Read body for non-GET methods
    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.headers.get("content-type", "").startswith("application/json") else {"raw": response.text},
                headers={"X-Proxied-To": backend_url},
            )
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail=f"Backend unavailable: {backend_url}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(e)}")
