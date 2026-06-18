---
name: dx_base_check_k8s_health_no_app_pool
description: Vérifie que la liveness/readiness n'utilise PAS la même session DB que le code applicatif (pool dédié ou bypass).
metadata:
  reference: § 5
---

# dx_base_check_k8s_health_no_app_pool

## Actions
Inspecter le handler readiness : doit utiliser un raw `SELECT 1` via engine direct, pas une session du pool app.
