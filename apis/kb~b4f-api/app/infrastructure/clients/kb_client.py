"""HTTP client for kb~backend-api."""
from shared.services import create_service_client
from shared.infrastructure import get_logger

logger = get_logger(__name__)


class KBClient:
    def __init__(self):
        self._client = create_service_client("kb~backend-api")

    # ── Categories ────────────────────────────

    async def list_categories(self, forward_headers=None):
        resp = await self._client.get("/api/v1/kb/categories", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_category(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/kb/categories", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_category(self, category_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/kb/categories/{category_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_category(self, category_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/kb/categories/{category_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    # ── Articles ──────────────────────────────

    async def list_articles(self, skip=0, limit=20, search=None, category_id=None, visibility=None, forward_headers=None):
        params = {"skip": str(skip), "limit": str(limit)}
        if search:
            params["search"] = search
        if category_id:
            params["category_id"] = category_id
        if visibility:
            params["visibility"] = visibility
        resp = await self._client.get("/api/v1/kb/articles", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def popular_articles(self, limit=10, forward_headers=None):
        params = {"limit": str(limit)}
        resp = await self._client.get("/api/v1/kb/articles/popular", params=params, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def create_article(self, data, forward_headers=None):
        resp = await self._client.post("/api/v1/kb/articles", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def get_article(self, slug_or_id, forward_headers=None):
        resp = await self._client.get(f"/api/v1/kb/articles/{slug_or_id}", forward_headers=forward_headers)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def update_article(self, article_id, data, forward_headers=None):
        resp = await self._client.patch(f"/api/v1/kb/articles/{article_id}", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    async def delete_article(self, article_id, forward_headers=None):
        resp = await self._client.delete(f"/api/v1/kb/articles/{article_id}", forward_headers=forward_headers)
        return resp.status_code == 204

    async def article_feedback(self, article_id, data, forward_headers=None):
        resp = await self._client.post(f"/api/v1/kb/articles/{article_id}/feedback", json=data, forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()

    # ── Stats ─────────────────────────────────

    async def get_stats(self, forward_headers=None):
        resp = await self._client.get("/api/v1/kb/stats", forward_headers=forward_headers)
        resp.raise_for_status()
        return resp.json()


kb_client = KBClient()
