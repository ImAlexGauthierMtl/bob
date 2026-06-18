---
name: dx_base_create_cicd_minimal_gitlab_yml_canonical
description: Génère le .gitlab-ci.yml minimal canonique d'un projet consommateur : 2 file-includes du repo croo-dev/ci-cd-unified-template-v1.0 avec ref taguée identique.
metadata:
  reference: § 4.1
---

# dx_base_create_cicd_minimal_gitlab_yml_canonical

## Sortie attendue
```yaml
include:
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1.0.64                  # pin strict
    file: '/kaniko.yml'
  - project: 'croo-dev/ci-cd-unified-template-v1.0'
    ref: v1.0.64
    file: '/templates/parent.yml'
```

## Refus
- `ref: main` — toujours un tag
- refs différentes entre les deux includes
- include vers `infrastructure/ci-templates` ou `shared/cicd-templates`
