---
name: dx_base_check_k8s_tls_chart_supports_both_modes
description: Vérifie que le chart api-chart supporte tls.strategy: wildcard OU tls.strategy: cert-manager via conditionnels.
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_tls_chart_supports_both_modes

## Actions
```bash
grep -E "tls.strategy" deploy/helm/api-chart/templates/*.yaml
```
Doit y avoir un `{{- if eq .Values.tls.strategy "cert-manager" }}` dans certificate.yaml et ingress.yaml.
