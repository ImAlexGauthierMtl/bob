---
name: dx_base_check_shared_three_layers
description: Vérifie l'existence et le périmètre des trois dossiers de code partagé (apis/shared, apis/exposed/shared, apis/internal/shared) et les règles de dépendance entre eux : exposed/shared ne consomme jamais internal/shared, apis/shared ne consomme aucun des deux.
metadata:
  reference: § 2.10 + § 8.7
---

# dx_base_check_shared_three_layers

## Règle
Trois niveaux de partage, sens de dépendance unidirectionnel.

## Actions
```bash
for d in apis/shared apis/exposed/shared apis/internal/shared; do
    [ -d "$d" ] || echo "WARN: $d absent (créer même vide si le projet a des APIs)"
done

# exposed/shared ne doit jamais importer internal/shared
grep -rE "from .*internal[._]shared|import .*internal[._]shared" \
    apis/exposed/shared/ 2>/dev/null \
    | grep . && echo "FAIL: exposed/shared importe internal/shared"

# apis/shared ne doit importer ni exposed ni internal
grep -rE "(exposed|internal)[._]shared" apis/shared/ 2>/dev/null \
    | grep . && echo "FAIL: apis/shared dépend d'une couche enfant"
```
