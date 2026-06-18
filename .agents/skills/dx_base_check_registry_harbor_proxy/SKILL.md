---
name: dx_base_check_registry_harbor_proxy
description: Vérifie que les pulls Docker Hub passent par le proxy Harbor (dockerhub-mirror.tools.thesmartcrew.com).
metadata:
  reference: § 7 + § 8.6
---

# dx_base_check_registry_harbor_proxy

## Actions
Confirmer que les jobs Kaniko utilisent l'image wrappée du repo partagé. Vérifier `KANIKO_IMAGE` :
```bash
grep -rE "KANIKO_IMAGE" .gitlab-ci.yml deploy/
```
Doit pointer vers `gitlab.tools.thesmartcrew.com:5050/croo-dev/ci-cd-unified-template-v1.0/kaniko:vX.Y.Z`.
