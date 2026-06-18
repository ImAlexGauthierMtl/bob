---
name: dx_base_check_k8s_trace_id_in_logs
description: Vérifie que les logs incluent trace_id et span_id pour permettre la corrélation logs ↔ traces.
metadata:
  reference: § 5
---

# dx_base_check_k8s_trace_id_in_logs

## Actions
```bash
grep -rE "trace_id|span_id" apis/*/src/ | grep -E "logger\.|extra=" || echo FAIL
```
