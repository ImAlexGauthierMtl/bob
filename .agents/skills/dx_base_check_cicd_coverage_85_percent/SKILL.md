---
name: dx_base_check_cicd_coverage_85_percent
description: Vérifie que le seuil de couverture est ≥ 85 % et que le pipeline échoue si en-dessous.
metadata:
  reference: § 4.7 + § 8.3
---

# dx_base_check_cicd_coverage_85_percent

## Actions
Chercher dans les jobs test : `--cov-fail-under=85` (pytest) ou seuil équivalent (jest, ng).
```bash
grep -rE "cov-fail-under|coverageThreshold" apis/ frontend/ ci/ .gitlab-ci.yml
```
