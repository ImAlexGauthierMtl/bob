---
name: dx_base_check_cicd_junit_cobertura_reports
description: Vérifie que les jobs test produisent des rapports JUnit + Cobertura uploadés en artifacts.
metadata:
  reference: § 4.7 + § 8.3
---

# dx_base_check_cicd_junit_cobertura_reports

## Actions
```bash
grep -B2 -A5 "artifacts:" .gitlab-ci.yml | grep -E "junit:|cobertura:"
```
