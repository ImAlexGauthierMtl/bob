---
name: dx_base_check_cicd_include_tag_version
description: Vérifie que l'include pointe vers un tag Semver (v1, v1.2.0), JAMAIS vers main ou master.
metadata:
  reference: § 4.1 + § 8.3
---

# dx_base_check_cicd_include_tag_version

## Actions
```bash
grep -E "ref:" .gitlab-ci.yml
```
Ne doit JAMAIS contenir `ref: main` ou `ref: master`. Doit matcher `^v\d+(\.\d+){0,2}$`.
