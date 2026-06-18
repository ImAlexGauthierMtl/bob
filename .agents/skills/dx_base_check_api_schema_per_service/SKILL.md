---
name: dx_base_check_api_schema_per_service
description: Vérifie que chaque Backend possède un schéma PG au nom du service (search_path et alembic version_table_schema).
metadata:
  reference: § 2.6 + § 8.1
---

# dx_base_check_api_schema_per_service

## Actions
```bash
for d in apis/internal/*-backend-api/; do
  svc=$(basename "$d" | sed 's/-backend-api//')
  grep -E "search_path|version_table_schema" "$d/alembic.ini" "$d/src/**/config.py" | grep -E "$svc" || echo "FAIL: $d sans schéma $svc"
done
```
