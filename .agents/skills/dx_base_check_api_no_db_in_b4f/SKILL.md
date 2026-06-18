---
name: dx_base_check_api_no_db_in_b4f
description: Vérifie qu'aucune B4F ne contient alembic/, modèles SQLAlchemy ou DATABASE_URL. Les B4F sont stateless.
metadata:
  reference: § 2.2 + § 8.1
---

# dx_base_check_api_no_db_in_b4f

## Règle
Une B4F ne dialogue jamais avec une DB.

## Actions
```bash
for d in apis/exposed/*-b4f-api/; do
  [ -d "$d/alembic" ] && echo "FAIL: $d a un alembic/"
  grep -rE "DATABASE_URL|sqlalchemy|alembic" "$d/src" && echo "FAIL: $d référence DB"
done
```
