---
name: dx_base_check_api_no_create_all_at_startup
description: Vérifie qu'AUCUNE API n'appelle metadata.create_all() ou db.create_all() au startup. Le schéma est géré exclusivement par Alembic.
metadata:
  reference: § 2.8 + § 8.1
---

# dx_base_check_api_no_create_all_at_startup

## Actions
```bash
grep -rE "metadata\.create_all|db\.create_all|Base\.metadata\.create_all" apis/ && echo FAIL
```
