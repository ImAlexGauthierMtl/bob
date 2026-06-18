---
name: dx_base_create_api_backend_scaffold
description: Crée le squelette d'une nouvelle Backend API sous apis/internal/<name>-backend-api/ : Dockerfile, pyproject, src/<name>_backend_api/ avec les 4 couches Clean Archi, alembic/, schéma PG dédié, migrate.sh, run_api.sh.
metadata:
  reference: § 2.1 + § 2.6 + § 12
---

# dx_base_create_api_backend_scaffold

## Refus
- Nom contient `authentication` → refuser, proposer split iam-backend + auth-b4f
- Pas de suffixe `-backend-api` → refuser

## Actions
Créer arborescence + alembic init + première migration créant CREATE SCHEMA IF NOT EXISTS <service>.
Wire SQLAlchemy avec pool_size=5, max_overflow=5, pool_pre_ping=True, prepared_statement_cache_size=0.
