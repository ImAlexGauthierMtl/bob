# Template: Client HTTP partagé (inter-services)

> Recette pour créer un client HTTP pour la communication inter-APIs.
> **Zéro décision** : suivre exactement ce pattern.

## Fichier à créer

`shared/services/http_client.py`

```python
"""HTTP client for inter-API communication."""

import httpx
from typing import Optional, Dict, Any
from ..infrastructure.logging import get_logger

logger = get_logger(__name__)


class HTTPClient:
    """HTTP client for making requests to other APIs."""

    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout

    def _full_url(self, url: str) -> str:
        if self.base_url and not url.startswith("http"):
            return f"{self.base_url}{url}"
        return url

    async def get(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> httpx.Response:
        """Make GET request."""
        full_url = self._full_url(url)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(full_url, headers=headers, **kwargs)
                logger.debug("http_request", method="GET", url=full_url, status_code=response.status_code)
                return response
        except Exception as e:
            logger.error("http_request_error", method="GET", url=full_url, error=str(e))
            raise

    async def post(self, url: str, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, **kwargs) -> httpx.Response:
        """Make POST request."""
        full_url = self._full_url(url)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(full_url, json=json, headers=headers, **kwargs)
                logger.debug("http_request", method="POST", url=full_url, status_code=response.status_code)
                return response
        except Exception as e:
            logger.error("http_request_error", method="POST", url=full_url, error=str(e))
            raise

    async def put(self, url: str, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, **kwargs) -> httpx.Response:
        """Make PUT request."""
        full_url = self._full_url(url)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(full_url, json=json, headers=headers, **kwargs)
                logger.debug("http_request", method="PUT", url=full_url, status_code=response.status_code)
                return response
        except Exception as e:
            logger.error("http_request_error", method="PUT", url=full_url, error=str(e))
            raise

    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs) -> httpx.Response:
        """Make DELETE request."""
        full_url = self._full_url(url)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(full_url, headers=headers, **kwargs)
                logger.debug("http_request", method="DELETE", url=full_url, status_code=response.status_code)
                return response
        except Exception as e:
            logger.error("http_request_error", method="DELETE", url=full_url, error=str(e))
            raise
```

## Utilisation dans un B4F API

```python
from shared.services.http_client import HTTPClient

client = HTTPClient(base_url="http://clients-backend-api:8002")
response = await client.get("/api/v1/clients")
data = response.json()
```

## Règles NON-NÉGOCIABLES

1. `httpx.AsyncClient` — jamais `requests` (blocking)
2. Timeout configurable (défaut 30s)
3. Structured logging pour chaque requête
4. Error logging avec méthode, URL, et erreur
5. Base URL optionnelle pour les appels inter-services
