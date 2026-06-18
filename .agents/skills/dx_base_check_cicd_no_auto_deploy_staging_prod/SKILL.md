---
name: dx_base_check_cicd_no_auto_deploy_staging_prod
description: Vérifie qu'aucun job ne déploie automatiquement en staging ou prod (manual trigger obligatoire).
metadata:
  reference: § 4 + § 8.3
---

# dx_base_check_cicd_no_auto_deploy_staging_prod

## Actions
```bash
grep -B3 "environment.*staging\|environment.*prod" .gitlab-ci.yml | grep "when: manual" || echo FAIL
```
