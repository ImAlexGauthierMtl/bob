---
name: dx_base_create_api_migration_initial
description: Crée la première migration Alembic d'une nouvelle Backend API : CREATE SCHEMA IF NOT EXISTS <service> puis création de la table principale.
metadata:
  reference: § 2.6 + § 2.8
---

# dx_base_create_api_migration_initial

## Actions
```bash
cd apis/internal/<service>-backend-api
alembic revision -m "create_schema_and_initial_tables"
```
Dans le fichier généré, en première instruction d'`upgrade()` :
```python
op.execute("CREATE SCHEMA IF NOT EXISTS <service>")
```
Configurer alembic.ini : `version_table_schema = <service>` et `search_path = <service>,public`.
