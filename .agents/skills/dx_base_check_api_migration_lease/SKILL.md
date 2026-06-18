---
name: dx_base_check_api_migration_lease
description: Vérifie que l'initContainer migrate utilise migrate_with_lease.py (Lease Kubernetes coordination.k8s.io) et non un lock Redis ni un alembic upgrade head direct. Vérifie MIGRATION_SERVICE + MIGRATION_NAMESPACE (fieldRef) et le RBAC Lease.
metadata:
  reference: § 2.7.5
---

# dx_base_check_api_migration_lease

## Règle (v1.4 doc)
La coordination des migrations passe par un **Lease Kubernetes** (`migration-<service>`). Redis est dédié à l'event bus — aucun lock de migration Redis.

## Actions
```bash
# 1. L'initContainer appelle migrate_with_lease.py
grep -rE "migrate_with_lease\.py" deploy/values/ apis/internal/*/Dockerfile 2>/dev/null \
    || echo "FAIL: migrate_with_lease.py non référencé"

# 2. Aucun résidu du lock Redis
grep -rE "migrate_with_lease\.py|migrations:lock|MIGRATION_LOCK_TTL_MS" \
    --include="*.py" --include="*.yaml" --include="*.yml" --include="*.sh" \
    apis/ deploy/ 2>/dev/null \
    | grep . && echo "FAIL: résidus du lock Redis"

# 3. Pas d'alembic upgrade head direct dans un initContainer
grep -rE 'command:.*alembic.*upgrade' deploy/values/ 2>/dev/null \
    | grep -v migrate_with_lease && echo "FAIL: alembic direct sans Lease"

# 4. Variables d'environnement du Lease (chart api-chart les injecte)
#    MIGRATION_SERVICE (apiName) + MIGRATION_NAMESPACE (fieldRef metadata.namespace)
#    → vérifier dans le rendu helm template si audit du chart
```

## RBAC attendu (template migration-lease-rbac.yaml du chart)
- Role : `create` sur leases (général) + `get/update/patch` sur `migration-<service>` (nommé)
- RoleBinding vers le ServiceAccount du pod
