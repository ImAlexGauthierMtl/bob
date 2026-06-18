---
name: dx_base_create_gateway_chart
description: Génère gateway-chart (Chart.yaml + values.yaml + templates : ingress.yaml unique, cert-copy-job.yaml, cert-copy-rbac.yaml, _helpers.tpl).
metadata:
  reference: § 5.11 + § 13.1
---

# dx_base_create_gateway_chart

## Actions
Créer `deploy/helm/gateway-chart/` du repo CI/CD partagé avec :
- `Chart.yaml` (name=gateway-chart, version=1.1.0)
- `values.yaml` : host, ingressClassName, tls.{secretName,sourceSecretName,sourceNamespace,enableCopyJob}, routes.{apis,frontend}, annotations (ssl-redirect, force-ssl-redirect, use-regex, rewrite-target)
- `templates/ingress.yaml` : un seul Ingress avec rules /api/<name>(/|$)(.*) puis catch-all /
- `templates/cert-copy-job.yaml` : Job pre-install/pre-upgrade qui kubectl get + apply
- `templates/cert-copy-rbac.yaml` : ServiceAccount + Role (reader cert-manager) + Role (writer namespace cible) avec RBAC minimal
- `templates/_helpers.tpl`
