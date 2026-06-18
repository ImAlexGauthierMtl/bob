---
name: dx_base_check_k8s_traceparent_propagation
description: Vérifie que les services propagent l'en-tête `traceparent` (W3C Trace Context) entre eux.
metadata:
  reference: § 5
---

# dx_base_check_k8s_traceparent_propagation

## Actions
```bash
grep -rE "traceparent|TraceContextTextMapPropagator|opentelemetry.propagate" apis/*/src/ || echo FAIL
```
