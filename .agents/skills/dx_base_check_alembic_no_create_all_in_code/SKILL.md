---
name: dx_base_check_alembic_no_create_all_in_code
description: Vérifie qu'aucun appel à metadata.create_all() ni db.create_all() ne subsiste dans le code (couvert mais explicite : doublon avec dx_base_check_api_no_create_all_at_startup pour traçabilité côté Alembic).
metadata:
  reference: § 2.7.5
---

# dx_base_check_alembic_no_create_all_in_code

## Actions
```bash
grep -rE "metadata\.create_all|db\.create_all|SQLModel\.metadata\.create_all|drop_all\(" \
  --include="*.py" apis/ \
  | grep -v "alembic/" \
  | grep . && echo FAIL
```
