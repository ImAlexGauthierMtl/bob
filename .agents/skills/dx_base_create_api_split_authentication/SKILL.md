---
name: dx_base_create_api_split_authentication
description: Refactor : sépare une API 'authentication' monolithique en iam-backend-api (DB users) + auth-b4f-api (login/logout/JWT). Crée les deux APIs, migre les routes, renomme le schéma DB en 'iam'.
metadata:
  reference: § 2.5
---

# dx_base_create_api_split_authentication

## Actions
1. Créer `apis/internal/iam-backend-api/` (schéma iam, modèles users/roles)
2. Créer `apis/exposed/auth-b4f-api/` (routes login/logout/refresh, appelle iam)
3. Migration Alembic : `ALTER SCHEMA authentication RENAME TO iam` (downtime court ou stratégie blue-green)
4. Mettre à jour les frontends pour pointer vers auth-b4f
5. Supprimer l'ancien `authentication` après bascule
