---
name: dx_base_check_k8s_no_base64_decode
description: Vérifie qu'aucun script ne fait `base64 -d` sur un kubeconfig (pratique fragile, source de bugs).
metadata:
  reference: § 5
---

# dx_base_check_k8s_no_base64_decode

## Actions
```bash
grep -rE "base64 -d|base64 --decode" deploy/scripts/ ci/ .gitlab-ci.yml && echo "FAIL: base64 -d sur kubeconfig"
```
