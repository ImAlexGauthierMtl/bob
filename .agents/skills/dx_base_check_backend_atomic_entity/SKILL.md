---
name: dx_base_check_backend_atomic_entity
description: Vérifie que chaque Backend expose UNE entité principale atomique (+ secondaires liées), sans logique d'affaire transverse ni agrégation multi-entités appartenant au B4F.
metadata:
  reference: § 2.3 + § 2.8
---

# dx_base_check_backend_atomic_entity

## Règle
Le Backend est le gardien d'**une entité atomique**. Pas de logique d'affaire transverse, pas d'agrégation cross-domaine (ça appartient au B4F).

## Actions
```bash
for d in apis/internal/*-backend-api/; do
  [ -d "$d/src" ] || continue
  name=$(basename "$d")

  # Compter les "entités principales" : agrégats racine dans domain/entities/
  ents=$(find "$d/src" -path "*domain/entities/*.py" ! -name "__init__.py" 2>/dev/null | wc -l)
  # Heuristique : beaucoup d'entités racines indépendantes = pas atomique
  [ "$ents" -gt 5 ] && echo "WARN: $name a $ents entités — vérifier l'atomicité (1 principale + secondaires liées)"

  # Signal de logique d'affaire transverse : appels HTTP sortants vers d'autres services
  grep -rqE "httpx|requests\.(get|post)" "$d/src" 2>/dev/null \
    && echo "FAIL: $name fait des appels HTTP sortants (agrégation = rôle du B4F ; sync = event bus)"

  # Signal d'agrégation multi-domaine : import de modèles d'un autre backend
  grep -rqE "from .*_backend_api" "$d/src" 2>/dev/null \
    && echo "FAIL: $name dépend d'un autre Backend (couplage interdit, § 2.3)"
done
```
