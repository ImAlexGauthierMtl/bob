---
name: dx_base_create_local_dev_compose
description: Génère un docker-compose.yml démarrant toutes les APIs, postgres, redis, frontend, avec volumes hot-reload et healthchecks.
metadata:
  reference: § 11
---

# dx_base_create_local_dev_compose

## Actions
Itérer sur apis/exposed/* et apis/internal/* pour générer un service par API.
Ajouter services postgres:16, redis:7, frontend.
Volumes : ./apis/.../src → /app/src ; ./frontend/src → /app/src.
