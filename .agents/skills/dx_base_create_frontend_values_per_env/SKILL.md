---
name: dx_base_create_frontend_values_per_env
description: Génère deploy/values/<env>/frontend.yaml. replicaCount, env_ (API_BASE_URL=/api, ENV_NAME), resources.
metadata:
  reference: § 5.12
---

# dx_base_create_frontend_values_per_env

## Contenu type
```yaml
replicaCount: 1   # 3 en prod
env_:
  - name: API_BASE_URL
    value: /api
  - name: ENV_NAME
    value: <env>
resources:
  requests: { cpu: 50m, memory: 64Mi }
  limits:   { cpu: 200m, memory: 256Mi }
```
