---
name: dx_base_check_gateway_routes_apis_under_api_prefix
description: Vérifie que chaque B4F est routée par le gateway sur /api/<service>(/|$)(.*) avec rewrite-target /$2.
metadata:
  reference: § 5.11 + § 8.4
---

# dx_base_check_gateway_routes_apis_under_api_prefix

## Actions
```bash
kubectl -n "$NAMESPACE" get ingress api-gateway -o yaml \
  | yq '.spec.rules[].http.paths[].path' \
  | grep -E "^/api/[a-z-]+\(/\|\$\)\(\.\*\)$" \
  || echo "FAIL: routes API absentes ou malformées"
```
Croiser avec `ls apis/exposed/` : chaque B4F doit avoir sa route.
