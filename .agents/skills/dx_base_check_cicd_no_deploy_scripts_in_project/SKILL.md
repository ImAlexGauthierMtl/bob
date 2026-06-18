---
name: dx_base_check_cicd_no_deploy_scripts_in_project
description: Vérifie qu'aucun script deploy/migrate/smoke n'est dupliqué dans le projet (ils vivent dans le repo partagé).
metadata:
  reference: § 4.1 + § 8.3
---

# dx_base_check_cicd_no_deploy_scripts_in_project

## Actions
```bash
find ci/ deploy/scripts/ scripts/ -name "deploy-api*" -o -name "smoke-test*" -o -name "migrate_with_lease*" 2>/dev/null       && echo "FAIL: scripts dupliqués"
```
