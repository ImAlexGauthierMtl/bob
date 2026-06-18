---
name: dx_base_check_cicd_smoke_test_endpoints
description: Vérifie qu'un job smoke-test post-deploy teste les endpoints critiques (health, readiness, route métier essentielle).
metadata:
  reference: § 4.11 + § 8.3
---

# dx_base_check_cicd_smoke_test_endpoints

## Actions
```bash
grep -E "smoke-test|smoke_test" .gitlab-ci.yml || echo FAIL
```
Inspecter `deploy/scripts/smoke-test.sh` (depuis le repo partagé) pour confirmer les endpoints.
