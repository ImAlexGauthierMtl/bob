---
name: dx_base_check_k8s_liveness_no_external_calls
description: Vérifie que la liveness probe ne fait pas d'appel externe (DB, Redis, autre service). Sinon, échec en cascade.
metadata:
  reference: § 5
---

# dx_base_check_k8s_liveness_no_external_calls

## Actions
Inspecter le code de `/healthz/live` : doit retourner 200 sans accéder à la DB ni à Redis (ces dépendances vont dans /healthz/ready).
