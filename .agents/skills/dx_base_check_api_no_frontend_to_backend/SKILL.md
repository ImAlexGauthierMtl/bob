---
name: dx_base_check_api_no_frontend_to_backend
description: Vérifie qu'aucune URL *-backend-api n'apparaît dans le code frontend (les Backends ne sont jamais appelés directement par le navigateur).
metadata:
  reference: § 2.2 + § 8.1
---

# dx_base_check_api_no_frontend_to_backend

## Actions
```bash
grep -rE "backend-api" frontend/src/ && echo "FAIL: frontend appelle un Backend"
```
