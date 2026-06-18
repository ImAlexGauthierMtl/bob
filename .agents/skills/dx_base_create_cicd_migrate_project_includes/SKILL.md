---
name: dx_base_create_cicd_migrate_project_includes
description: Migre le .gitlab-ci.yml d'un projet vers le format canonique : 2 file-includes du repo croo-dev/ci-cd-unified-template-v1.0 (/kaniko.yml + /templates/parent.yml, même ref taguée). Remplace toute référence à infrastructure/ci-templates.
metadata:
  reference: § 4.1
---

# dx_base_create_cicd_migrate_project_includes

## Actions
1. Lire `.gitlab-ci.yml`
2. Remplacer tout include `project: 'infrastructure/ci-templates'` par `project: 'croo-dev/ci-cd-unified-template-v1.0'` (le `/kaniko.yml` y vit désormais)
3. Harmoniser les `ref:` des deux includes sur le même tag (jamais `main`)
4. Vérifier avec `dx_base_check_cicd_canonical_includes`

## Rétrocompatibilité
Les projets qui référencent encore `infrastructure/ci-templates` continuent de fonctionner tant que ce repo existe, mais doivent migrer : le `kaniko.yml` du repo unifié est la seule version maintenue.
