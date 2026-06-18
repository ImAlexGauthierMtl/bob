---
name: dx_base_check_api_rolling_update_strategy
description: Vérifie que la stratégie de déploiement est RollingUpdate avec maxSurge:1 et maxUnavailable:0 (zero-downtime).
metadata:
  reference: § 2.8 + § 8.1
---

# dx_base_check_api_rolling_update_strategy

## Actions
```bash
grep -rA3 "strategy:" deploy/helm/*/templates/deployment.yaml
```
Doit contenir : type: RollingUpdate, maxSurge: 1, maxUnavailable: 0.
