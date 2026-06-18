---
name: dx_base_check_cicd_no_latest_tag_in_deploy
description: Vérifie que les manifestes de déploiement n'utilisent jamais `:latest`.
metadata:
  reference: § 7 + § 8.3
---

# dx_base_check_cicd_no_latest_tag_in_deploy

## Actions
```bash
grep -rE "image:.*:latest" deploy/values/ deploy/helm/ && echo FAIL
```
