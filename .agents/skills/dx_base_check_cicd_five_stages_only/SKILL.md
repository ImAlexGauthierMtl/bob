---
name: dx_base_check_cicd_five_stages_only
description: Vérifie que la pipeline ne contient QUE 5 stages : test, build, deploy, smoke-test, rollback. Pas de stage migration séparé (cf. initContainer).
metadata:
  reference: § 4.3 + § 8.3
---

# dx_base_check_cicd_five_stages_only

## Actions
```bash
grep -A10 "^stages:" .gitlab-ci.yml
```
Comparer à la liste : test, build, deploy, smoke-test, rollback.
