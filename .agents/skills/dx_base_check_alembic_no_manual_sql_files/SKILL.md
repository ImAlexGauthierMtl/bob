---
name: dx_base_check_alembic_no_manual_sql_files
description: Vérifie qu'aucun fichier .sql artisanal (init.sql, seed.sql, schema.sql) n'existe en dehors des révisions Alembic.
metadata:
  reference: § 2.7.5
---

# dx_base_check_alembic_no_manual_sql_files

## Actions
```bash
find . -type f -name "*.sql" \
  ! -path "*/alembic/versions/*" \
  ! -path "*/node_modules/*" \
  ! -path "*/.git/*" \
  ! -path "*/tests/fixtures/*" \
  | grep . && echo "FAIL: fichiers SQL artisanaux trouvés"
```
Exception tolérée : `tests/fixtures/*.sql` (fixtures de test). Toute autre apparition est une violation.
