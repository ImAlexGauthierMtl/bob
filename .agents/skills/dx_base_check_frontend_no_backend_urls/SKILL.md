---
name: dx_base_check_frontend_no_backend_urls
description: Vérifie qu'aucune URL d'une Backend API n'apparaît dans le code frontend.
metadata:
  reference: § 2.2 + § 8.2
---

# dx_base_check_frontend_no_backend_urls

## Actions
```bash
grep -rE "[a-z-]+-backend-api" frontend/src/ && echo FAIL
```
