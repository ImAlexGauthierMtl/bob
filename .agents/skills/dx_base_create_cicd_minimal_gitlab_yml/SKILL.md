---
name: dx_base_create_cicd_minimal_gitlab_yml
description: Génère un .gitlab-ci.yml minimal pour un projet : include du repo partagé pinned sur tag, variables d'overrides, rien d'autre.
metadata:
  reference: § 4.1 + § 8.3
---

# dx_base_create_cicd_minimal_gitlab_yml

## Sortie attendue
```yaml
include:
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1
    file: '/templates/parent.yml'

variables:
  PROJECT_NAME: <my-project>
```
