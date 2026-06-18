---
name: dx_base_check_k8s_otel_sampling
description: Vérifie qu'un sampling OTel est configuré (par défaut ratio 0.1 en prod, 1.0 en dev/staging).
metadata:
  reference: § 5
---

# dx_base_check_k8s_otel_sampling

## Actions
```bash
grep -rE "OTEL_TRACES_SAMPLER" deploy/values/ apis/ || echo "WARN: sampler non configuré"
```
