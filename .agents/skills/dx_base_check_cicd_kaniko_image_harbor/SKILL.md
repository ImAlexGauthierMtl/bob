---
name: dx_base_check_cicd_kaniko_image_harbor
description: Vérifie que KANIKO_IMAGE pointe vers l'image Kaniko wrappée publiée dans Harbor, et qu'aucun job n'utilise gcr.io/kaniko-project directement.
metadata:
  reference: § 4.10 + § 7
---

# dx_base_check_cicd_kaniko_image_harbor

## Actions
```bash
# 1. Pas d'usage direct de l'executor upstream
grep -rE "gcr\.io/kaniko-project" \
    --include="*.yml" --include="*.yaml" \
    .gitlab-ci.yml templates/ 2>/dev/null \
    | grep -v "kaniko/Dockerfile" \
    | grep . && echo "FAIL: usage direct gcr.io/kaniko-project (utiliser l'image wrappée Harbor)"

# 2. KANIKO_IMAGE pointe vers Harbor
grep -rE "KANIKO_IMAGE:" kaniko.yml .gitlab-ci.yml 2>/dev/null \
    | grep -vqE "harbor\." && echo "WARN: KANIKO_IMAGE ne pointe pas vers Harbor"
```
