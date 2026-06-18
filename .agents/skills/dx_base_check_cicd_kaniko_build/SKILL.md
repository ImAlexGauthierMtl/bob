---
name: dx_base_check_cicd_kaniko_build
description: Vérifie que tous les jobs build étendent .kaniko_build (ou .kaniko_frontend_build) du repo partagé.
metadata:
  reference: § 4.10 + § 8.3
---

# dx_base_check_cicd_kaniko_build

## Actions
```bash
grep -B5 "stage: build" .gitlab-ci.yml | grep -E "extends:.*kaniko_(build|frontend_build)"
```
