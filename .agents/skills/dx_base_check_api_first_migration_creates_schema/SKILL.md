---
name: dx_base_check_api_first_migration_creates_schema
description: Vérifie que la première migration Alembic crée le schéma PG (CREATE SCHEMA IF NOT EXISTS <service>) avant tout DDL.
metadata:
  reference: § 2.6 + § 2.8
---

# dx_base_check_api_first_migration_creates_schema

## Actions
```bash
head -50 apis/internal/*/alembic/versions/0001_*.py | grep -E "CREATE SCHEMA"
```
Si absent dans une première migration → FAIL.
