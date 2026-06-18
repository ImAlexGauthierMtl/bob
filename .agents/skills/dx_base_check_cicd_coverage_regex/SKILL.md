---
name: dx_base_check_cicd_coverage_regex
description: Vérifie que coverage_report est configuré et qu'un coverage regex affiche le pourcentage dans GitLab UI.
metadata:
  reference: § 4.7
---

# dx_base_check_cicd_coverage_regex

## Actions
```bash
grep -E "coverage:|coverage_report" .gitlab-ci.yml
```
