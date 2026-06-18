---
name: dx_base_create_local_dev_env_example
description: Génère un .env.example complet avec les variables nécessaires pour tourner en local (DB, Redis, URLs internes).
metadata:
  reference: § 11
---

# dx_base_create_local_dev_env_example

## Sortie
DB_HOST=postgres, DB_USERNAME=devuser, DB_PASSWORD=devpass, DB_DATABASE=app,
REDIS_URL=redis://redis:6379/0,
plus une variable par B4F pour pointer vers son Backend (`IAM_BACKEND_URL=http://iam-backend-api:8000`).
