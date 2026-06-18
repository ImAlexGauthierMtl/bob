---
name: dx_base_check_api_no_prepared_statements
description: Vérifie que les prepared statements SQLAlchemy sont désactivés (incompatible avec PgBouncer transaction-mode).
metadata:
  reference: § 2.7 + § 8.1
---

# dx_base_check_api_no_prepared_statements

## Actions
```bash
grep -rE "prepared_statement_cache_size|use_prepared|prepared=True" apis/internal/*/src/
```
Tout `prepared_statement_cache_size > 0` → FAIL.
