---
name: dx_base_analyse_api_inter_backend_http
description: Détecte les appels HTTP inter-Backend (violation de § 2.3). Doivent passer par Redis.
metadata:
  reference: § 2.3
---

# dx_base_analyse_api_inter_backend_http

## Actions
```bash
grep -rE "(httpx|requests|aiohttp)" apis/internal/*/src/       | grep -E "backend-api"       | grep -v "self"
```
