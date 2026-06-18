---
name: dx_base_check_api_migration_initcontainer
description: Vérifie que les migrations Alembic tournent via un initContainer K8s, jamais depuis le runner CI.
metadata:
  reference: § 2.8 + § 8.1
---

# dx_base_check_api_migration_initcontainer

## Actions
Inspecter deployment.yaml (chart) : initContainers doit contenir 'migrate' avec scripts/migrate_with_lease.py. Aucun job CI `alembic upgrade` ne doit exister.
```bash
grep -rE "alembic upgrade" .gitlab-ci.yml ci/ deploy/scripts/ | grep -v "migrate_with_lease"
```
