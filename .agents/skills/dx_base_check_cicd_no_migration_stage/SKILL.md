---
name: dx_base_check_cicd_no_migration_stage
description: Vérifie qu'aucun stage 'migration' ou 'migrate' n'est défini (les migrations tournent dans un initContainer, pas dans la pipeline).
metadata:
  reference: § 4.3 + § 2.8
---

# dx_base_check_cicd_no_migration_stage

## Actions
```bash
grep -E "stage:.*migrat" .gitlab-ci.yml && echo FAIL
```
