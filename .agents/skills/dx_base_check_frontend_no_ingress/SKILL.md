---
name: dx_base_check_frontend_no_ingress
description: Vérifie que le frontend n'a pas son propre Ingress (exposition via gateway uniquement).
metadata:
  reference: § 5.12 + § 5.11
---

# dx_base_check_frontend_no_ingress

## Actions
```bash
kubectl -n "$NAMESPACE" get ingress -l app.kubernetes.io/component=frontend \
  -o name 2>/dev/null | grep -q . && echo "FAIL: frontend a son propre Ingress"
```
