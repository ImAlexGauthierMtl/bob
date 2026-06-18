---
name: dx_base_check_frontend_e2e_not_in_ci
description: Vérifie qu'aucun job CI n'exécute les E2E (lourds, runner-killer). Ils tournent en pre-commit hook + post-deploy smoke-tests.
metadata:
  reference: § 3.5 + § 8.2 + § 4.11
---

# dx_base_check_frontend_e2e_not_in_ci

## Actions
```bash
grep -rE "cypress|playwright|e2e" .gitlab-ci.yml ci/       | grep -vE "(smoke|README|comment)"       && echo FAIL
```
