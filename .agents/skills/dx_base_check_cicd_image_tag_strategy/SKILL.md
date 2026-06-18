---
name: dx_base_check_cicd_image_tag_strategy
description: Vérifie la stratégie de tag : SHA + short SHA + latest ; les déploiements utilisent SHA, jamais latest.
metadata:
  reference: § 4 + § 7
---

# dx_base_check_cicd_image_tag_strategy

## Actions
```bash
grep -E "CI_COMMIT_SHA|CI_COMMIT_SHORT_SHA" deploy/values/*.yaml | grep image && echo OK
grep -E "image.*:latest" deploy/values/*.yaml && echo "FAIL: :latest en déploiement"
```
