---
name: dx_base_check_frontend_api_base_url_is_api
description: Vérifie que API_BASE_URL du frontend vaut /api (origine unique, jamais cross-domain).
metadata:
  reference: § 5.12 + § 8.4
---

# dx_base_check_frontend_api_base_url_is_api

## Actions
```bash
val=$(kubectl -n "$NAMESPACE" get deployment frontend \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="API_BASE_URL")].value}')
[ "$val" = "/api" ] || echo "FAIL: API_BASE_URL='$val' (attendu: /api)"
```
