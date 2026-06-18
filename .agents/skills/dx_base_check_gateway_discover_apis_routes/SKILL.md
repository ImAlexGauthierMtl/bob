---
name: dx_base_check_gateway_discover_apis_routes
description: Vérifie que les routes du gateway sont générées par discover-apis.sh (scan apis/exposed/), jamais codées en dur dans gateway-chart/values.yaml.
metadata:
  reference: § 5.11
---

# dx_base_check_gateway_discover_apis_routes

## Actions
```bash
# Dans gateway-chart/values.yaml, routes.apis doit être [] par défaut
yq '.routes.apis | length' /tmp/cicd-templates/deploy/helm/gateway-chart/values.yaml \
  | grep -q "^0$" \
  || echo "FAIL: routes.apis pré-rempli dans values.yaml (doit être généré)"

# deploy-gateway.sh doit scanner apis/exposed/
grep -q "apis/exposed" /tmp/cicd-templates/deploy/scripts/deploy-gateway.sh \
  || echo "FAIL: deploy-gateway.sh ne scanne pas apis/exposed/"
```
