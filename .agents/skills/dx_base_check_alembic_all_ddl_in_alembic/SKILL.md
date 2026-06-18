---
name: dx_base_check_alembic_all_ddl_in_alembic
description: Vérifie que toute DDL passe par Alembic : aucun fichier .sql exécuté hors d'Alembic, aucun CREATE SCHEMA/TABLE/INDEX dans le code applicatif ou dans des scripts shell.
metadata:
  reference: § 2.7.5 + § 8.1
---

# dx_base_check_alembic_all_ddl_in_alembic

## Règle
Toute opération DDL (création schéma, tables, index, droits, seeds reproductibles) **doit** être une révision Alembic. Aucun fichier `.sql` manuel.

## Actions
```bash
# 1. Aucun fichier .sql hors apis/internal/*/alembic/
find . -name "*.sql" -type f \
  | grep -vE "(alembic/versions/|node_modules/|.git/)" \
  | grep . && echo "FAIL: fichiers .sql hors d'Alembic"

# 2. Aucun script qui passe par psql
grep -rE "psql.*-f|psql.*<" \
  --include="*.sh" --include="*.py" \
  apis/ deploy/ scripts/ 2>/dev/null \
  && echo "FAIL: psql -f utilisé"

# 3. Aucun CREATE SCHEMA / CREATE TABLE dans le code applicatif
grep -rEi "(CREATE|DROP) (SCHEMA|TABLE|INDEX|TYPE|EXTENSION)" \
  --include="*.py" \
  apis/internal/*/src/ 2>/dev/null \
  | grep -v alembic/versions/ \
  | grep . && echo "FAIL: DDL dans le code applicatif"
```
