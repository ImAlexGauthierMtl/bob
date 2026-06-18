---
name: dx_base_check_api_no_http_between_backends
description: Vérifie qu'aucun Backend n'effectue d'appel HTTP vers un autre *-backend-api. La communication inter-Backend passe exclusivement par l'event bus Redis.
metadata:
  reference: § 2.3 + § 8.1
---

# dx_base_check_api_no_http_between_backends

## Actions
```bash
grep -rE "(httpx|requests|aiohttp).*backend-api" apis/internal/ && echo FAIL
```
