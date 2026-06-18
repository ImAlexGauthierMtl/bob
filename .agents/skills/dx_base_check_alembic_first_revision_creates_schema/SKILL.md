---
name: dx_base_check_alembic_first_revision_creates_schema
description: Vérifie que la première migration Alembic d'un Backend exécute CREATE SCHEMA IF NOT EXISTS <service> avant toute autre DDL.
metadata:
  reference: § 2.6 + § 2.7.5
---

# dx_base_check_alembic_first_revision_creates_schema

## Actions
```bash
for d in apis/internal/*-backend-api/; do
  svc=$(basename "$d" | sed 's/-backend-api//')
  first=$(ls "$d/alembic/versions/" 2>/dev/null | sort | head -1)
  [ -n "$first" ] || { echo "FAIL: $d sans première migration"; continue; }
  full="$d/alembic/versions/$first"
  grep -qE "CREATE SCHEMA IF NOT EXISTS \"?$svc\"?" "$full" \
    || echo "FAIL: $full ne crée pas le schéma $svc"
  # Downgrade doit drop le schéma
  grep -qE "DROP SCHEMA .* CASCADE" "$full" \
    || echo "FAIL: $full pas de DROP SCHEMA dans downgrade"
done
```
