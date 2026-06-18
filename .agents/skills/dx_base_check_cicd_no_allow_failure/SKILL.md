---
name: dx_base_check_cicd_no_allow_failure
description: Vérifie qu'aucun job critique (test, build, deploy) n'utilise `allow_failure: true`.
metadata:
  reference: § 4.6 + § 8.3
---

# dx_base_check_cicd_no_allow_failure

## Actions
```bash
grep -B2 "allow_failure: true" .gitlab-ci.yml && echo "FAIL: allow_failure détecté"
```
