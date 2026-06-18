---
name: dx_base_create_split_responsibilities_b4f_backend
description: Refactore une API qui mélange les responsabilités : remonte la logique d'affaire/agrégation/filtrage vers le B4F (par domaine frontend) et redescend l'infra (DB, services externes, fichiers) vers des Backend atomiques.
metadata:
  reference: § 2.2 + § 2.3 + § 2.8
---

# dx_base_create_split_responsibilities_b4f_backend

## Actions
1. **Cartographier** les responsabilités mélangées dans l'API cible
2. **Backend(s) atomique(s)** : pour chaque entité principale, créer/garder un `<entity>-backend-api` portant DB + migrations + services externes + fichiers de cette entité, sans dépendance vers d'autres Backends (event bus si besoin)
3. **B4F par domaine d'affaire** : créer/garder un `<domaine>-b4f-api` aligné sur une feature frontend, qui orchestre la logique d'affaire, agrège/filtre les données issues des Backend via DNS interne, et optimise les payloads pour l'écran
4. **Déléguer** : déplacer tout I/O fichier, appel externe, accès DB hors du B4F vers le(s) Backend(s)
5. Vérifier avec `dx_base_check_b4f_holds_business_logic`, `dx_base_check_backend_atomic_entity`, `dx_base_check_backend_owns_infrastructure`

## Refus
- Refuser de laisser de la logique d'affaire transverse dans un Backend
- Refuser de laisser un accès fichier/DB/externe dans un B4F
- Refuser un Backend portant plusieurs entités principales indépendantes
