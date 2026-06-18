---
name: dx_base_check_frontend_chart_exists
description: Vérifie que le frontend est packagé comme un chart Helm dédié (frontend-chart), paritaire avec api-chart.
metadata:
  reference: § 5.12 + § 13.1 + § 8.4
---

# dx_base_check_frontend_chart_exists

## Actions
```bash
# Dans le repo CI/CD partagé
[ -d /tmp/cicd-templates/deploy/helm/frontend-chart ] || echo "FAIL: frontend-chart absent"

# En cluster
helm -n "$NAMESPACE" status frontend >/dev/null 2>&1 || echo "FAIL: release 'frontend' absente"
kubectl -n "$NAMESPACE" get deployment frontend -o name || echo "FAIL: deployment frontend absent"
kubectl -n "$NAMESPACE" get service frontend -o name || echo "FAIL: service frontend absent"
```
