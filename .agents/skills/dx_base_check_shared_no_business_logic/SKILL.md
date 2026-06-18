---
name: dx_base_check_shared_no_business_logic
description: Vérifie qu'aucune logique métier ni modèle d'entité métier ne se trouve dans les shared/ : pas de use case, pas d'entité de domaine, pas de modèle SQLAlchemy d'entité dans apis/internal/shared.
metadata:
  reference: § 2.10
---

# dx_base_check_shared_no_business_logic

## Actions
```bash
# Pas de use_case dans shared/
find apis/shared apis/exposed/shared apis/internal/shared -path "*use_case*" 2>/dev/null \
    | grep . && echo "FAIL: use case dans shared/"

# Pas d'entité métier / modèle d'entité dans internal/shared
grep -rE "class .*\(Base\)|__tablename__" apis/internal/shared/ 2>/dev/null \
    | grep . && echo "FAIL: modèle d'entité métier dans internal/shared (les entités vivent par Backend)"

# Pas de dossier domain/ dans un shared/
find apis/shared apis/exposed/shared apis/internal/shared -type d -name domain 2>/dev/null \
    | grep . && echo "FAIL: dossier domain/ dans un shared/"
```
