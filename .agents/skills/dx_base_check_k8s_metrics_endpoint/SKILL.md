---
name: dx_base_check_k8s_metrics_endpoint
description: Vérifie qu'un endpoint /metrics Prometheus est exposé par chaque API.
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_metrics_endpoint

## Actions
```bash
grep -rE "/metrics|prometheus_client|prometheus-fastapi-instrumentator" apis/*/src/ || echo FAIL
```
