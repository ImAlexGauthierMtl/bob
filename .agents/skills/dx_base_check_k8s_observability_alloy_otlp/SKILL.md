---
name: dx_base_check_k8s_observability_alloy_otlp
description: Vérifie que Grafana Alloy (OTLP receiver) est référencé comme cible des traces/metrics, pas de Datadog/New Relic propriétaire.
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_observability_alloy_otlp

## Actions
```bash
grep -rE "OTEL_EXPORTER_OTLP_ENDPOINT" deploy/ apis/ | grep -E "alloy" || echo "WARN: cible OTLP non Alloy"
grep -rE "(datadog|newrelic|dynatrace)" deploy/ apis/ && echo "FAIL: agent propriétaire détecté"
```
