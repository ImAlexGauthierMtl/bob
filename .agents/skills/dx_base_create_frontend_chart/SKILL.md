---
name: dx_base_create_frontend_chart
description: Génère frontend-chart (Chart.yaml + values.yaml + templates : deployment.yaml, service.yaml ClusterIP, _helpers.tpl). PAS d'Ingress.
metadata:
  reference: § 5.12 + § 13.1
---

# dx_base_create_frontend_chart

## Actions
Créer `deploy/helm/frontend-chart/` avec :
- `Chart.yaml` (name=frontend-chart, version=1.1.0)
- `values.yaml` : image, replicaCount, service (ClusterIP, port 80, targetPort 80), probes (/healthz statique), resources, env_ (avec API_BASE_URL=/api)
- `templates/deployment.yaml` : RollingUpdate maxSurge:1 maxUnavailable:0, probes statiques
- `templates/service.yaml` : ClusterIP
- `templates/_helpers.tpl`
Refus : ne PAS générer de templates/ingress.yaml.
