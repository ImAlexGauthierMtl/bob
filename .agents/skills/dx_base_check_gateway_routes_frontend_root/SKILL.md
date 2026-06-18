---
name: dx_base_check_gateway_routes_frontend_root
description: Vérifie que l'Ingress gateway (api-gateway) route / vers le Service frontend (path: / pathType: Prefix).
metadata:
  reference: § 5.11 + § 8.4
---

# dx_base_check_gateway_routes_frontend_root

## Actions
```bash
kubectl -n "$NAMESPACE" get ingress api-gateway -o yaml \
  | yq '.spec.rules[].http.paths[] | select(.path == "/")' \
  | grep "name: frontend" || echo FAIL
```
