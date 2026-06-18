---
name: dx_base_check_k8s_health_endpoints
description: Vérifie que chaque API expose /healthz/live et /healthz/ready (probes K8s).
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_health_endpoints

## Actions
```bash
grep -rE "/healthz/(live|ready)|livenessProbe|readinessProbe" apis/*/src/ deploy/helm/*/templates/deployment.yaml
```
