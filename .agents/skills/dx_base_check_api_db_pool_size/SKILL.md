---
name: dx_base_check_api_db_pool_size
description: Vérifie que pool_size ≤ 5, max_overflow ≤ 5, pool_pre_ping=True dans la config SQLAlchemy (compatibilité PgBouncer transaction-mode).
metadata:
  reference: § 2.7 + § 8.1
---

# dx_base_check_api_db_pool_size

## Actions
```bash
grep -rE "pool_size|max_overflow|pool_pre_ping" apis/internal/*/src/
```
Valider : pool_size ≤ 5, max_overflow ≤ 5, pool_pre_ping=True.
