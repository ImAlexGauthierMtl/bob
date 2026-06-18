---
name: dx_base_check_cicd_artifacts_always
description: Vérifie que les jobs test utilisent `when: always` pour les artifacts (récupérables même en échec).
metadata:
  reference: § 4.7 + § 8.3
---

# dx_base_check_cicd_artifacts_always

## Actions
```bash
grep -B5 "junit:" .gitlab-ci.yml | grep "when: always" || echo "WARN: artifacts pas en when:always"
```
