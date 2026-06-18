---
name: dx_base_check_api_helm_wait_with_logs
description: Vérifie que le déploiement Helm utilise --wait et qu'en cas d'échec, les logs des initContainers et pods sont récupérés.
metadata:
  reference: § 2.8 + § 8.1
---

# dx_base_check_api_helm_wait_with_logs

## Actions
```bash
grep -rE "helm upgrade.*--wait" deploy/scripts/ || echo "FAIL: pas de --wait"
grep -rE "kubectl logs.*-c migrate" deploy/scripts/ || echo "FAIL: pas de récupération de logs initContainer"
```
