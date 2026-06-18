---
name: dx_base_check_gateway_chart_exists
description: Vérifie que gateway-chart est présent dans le repo CI/CD partagé et déployé en cluster.
metadata:
  reference: § 5.11 + § 13.1
---

# dx_base_check_gateway_chart_exists

## Actions
```bash
[ -d /tmp/cicd-templates/deploy/helm/gateway-chart ] || echo "FAIL: gateway-chart absent du repo CI/CD"

for tmpl in ingress.yaml cert-copy-job.yaml cert-copy-rbac.yaml; do
  [ -f /tmp/cicd-templates/deploy/helm/gateway-chart/templates/$tmpl ] \
    || echo "FAIL: gateway-chart/templates/$tmpl absent"
done

helm -n "$NAMESPACE" status api-gateway >/dev/null 2>&1 \
  || echo "FAIL: release 'api-gateway' absente"
```
