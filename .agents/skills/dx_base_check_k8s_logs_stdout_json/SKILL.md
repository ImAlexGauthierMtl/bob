---
name: dx_base_check_k8s_logs_stdout_json
description: Vérifie que les APIs émettent leurs logs en JSON structuré sur stdout (pas de fichier, pas de syslog).
metadata:
  reference: § 5 + § 8.4
---

# dx_base_check_k8s_logs_stdout_json

## Actions
```bash
grep -rE "logging.*json|JsonFormatter|python-json-logger" apis/*/src/ pyproject.toml || echo "FAIL: logs non JSON"
```
