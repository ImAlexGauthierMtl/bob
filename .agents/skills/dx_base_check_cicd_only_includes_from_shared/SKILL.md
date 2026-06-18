---
name: dx_base_check_cicd_only_includes_from_shared
description: Vérifie que le .gitlab-ci.yml du projet ne contient QUE des `include: project: croo-dev/ci-cd-unified-template-v1.0` (aucune logique inline).
metadata:
  reference: § 4.1 + § 8.3
---

# dx_base_check_cicd_only_includes_from_shared

## Actions
```bash
wc -l .gitlab-ci.yml
grep -cE "^[a-z_-]+:$" .gitlab-ci.yml  # jobs définis localement
grep -E "^include:" .gitlab-ci.yml || echo FAIL
```
Idéalement : 0 jobs inline, uniquement include + variables d'overrides.
