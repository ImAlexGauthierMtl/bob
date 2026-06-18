---
name: dx_base_check_k8s_trace_id_in_events
description: Vérifie que les messages publiés sur Redis incluent un champ trace_id pour le tracing distribué.
metadata:
  reference: § 5
---

# dx_base_check_k8s_trace_id_in_events

## Actions
```bash
grep -rE "trace_id" apis/internal/*/src/infrastructure/messaging/ || echo "WARN: trace_id absent des events"
```
