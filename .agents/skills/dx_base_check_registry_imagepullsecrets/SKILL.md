---
name: dx_base_check_registry_imagepullsecrets
description: Vérifie que les pods ont un imagePullSecret référencé pour authentifier les pulls depuis le GitLab Registry.
metadata:
  reference: § 7 + § 8.6
---

# dx_base_check_registry_imagepullsecrets

## Actions
```bash
grep -rE "imagePullSecrets" deploy/helm/*/templates/deployment.yaml || echo FAIL
```
