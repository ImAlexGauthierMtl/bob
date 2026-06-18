---
name: dx_base_check_b4f_grouped_by_business_domain
description: Vérifie que chaque B4F correspond à un domaine d'affaire aligné sur le découpage du frontend (mapping 1:1 avec une feature NGRX), et non à une entité technique isolée.
metadata:
  reference: § 2.2 + § 3.4
---

# dx_base_check_b4f_grouped_by_business_domain

## Règle
Les B4F sont regroupés **par domaine d'affaire = découpage du frontend**. Un B4F = une section/feature de l'UI (mapping 1:1, cf. § 3.4).

## Actions
```bash
# Pour chaque B4F, il devrait exister une feature NGRX du même nom de domaine
for d in apis/exposed/*-b4f-api/; do
  [ -d "$d" ] || continue
  dom=$(basename "$d" | sed 's/-b4f-api//')
  if [ -d frontend/src/app ]; then
    find frontend/src/app -type d -path "*features/$dom*" 2>/dev/null | grep -q . \
      || echo "WARN: B4F '$dom' sans feature frontend correspondante (mapping 1:1 attendu, § 3.4)"
  fi
done

# Un nom de B4F qui colle à une entité atomique de Backend est suspect
# (le B4F doit porter un domaine, pas une table)
for d in apis/exposed/*-b4f-api/; do
  dom=$(basename "$d" | sed 's/-b4f-api//')
  [ -d "apis/internal/${dom}-backend-api" ] \
    && echo "WARN: B4F '$dom' porte le même nom qu'un Backend atomique — vérifier que c'est bien un domaine d'affaire, pas un proxy d'entité"
done
```
