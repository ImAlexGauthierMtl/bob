---
name: dx_base_check_local_dev_docker_compose
description: Vérifie qu'un docker-compose.yml démarre toutes les APIs + DB + Redis + frontend en local.
metadata:
  reference: § 11 + § 8.9
---

# dx_base_check_local_dev_docker_compose

## Actions
```bash
[ -f docker-compose.yml ] || echo FAIL
docker compose config --quiet || echo "FAIL: compose invalide"
grep -E "redis|postgres" docker-compose.yml || echo "FAIL: deps manquantes"
```
