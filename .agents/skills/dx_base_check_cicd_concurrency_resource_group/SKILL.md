---
name: dx_base_check_cicd_concurrency_resource_group
description: Vérifie que les jobs deploy utilisent `resource_group` pour sérialiser les déploiements concurrents par environnement.
metadata:
  reference: § 4
---

# dx_base_check_cicd_concurrency_resource_group

## Actions
```bash
grep -B3 "stage: deploy" .gitlab-ci.yml | grep -E "resource_group:" || echo "WARN: pas de resource_group"
```
