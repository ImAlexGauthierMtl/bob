---
name: dx_base_check_api_event_bus_redis
description: Vérifie qu'un Redis est configuré (event bus) dans docker-compose et Helm. Les Backends publient/souscrivent uniquement via Redis pour le cross-domain.
metadata:
  reference: § 2.3 + § 8.1
---

# dx_base_check_api_event_bus_redis

## Actions
```bash
grep -E "image:.*redis" docker-compose.yml || echo "FAIL: pas de Redis dans compose"
grep -rE "redis" deploy/values/ || echo "FAIL: pas de Redis dans Helm values"
```
