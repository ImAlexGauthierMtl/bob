---
name: dx_intermediate_analyse_cicd_repo
description: Analyse la structure du repo CI/CD partagé (ci-cd-unified-template-v1.0) selon le chapitre 13. À invoquer pour auditer l'arborescence templates/, deploy/scripts/, deploy/helm/api-chart/, lint/, examples/, tests/. Vérifie aussi le versioning Semver, les tests automatisés (shellcheck, helm lint, intégration) et les règles de contribution.
metadata:
  reference: § 13 de docs/architecture/regles-architecture-deploiement.md
  target_repo: git@gitlab.tools.thesmartcrew.com:croo-dev/ci-cd-unified-template-v1.0.git
---

# dx_intermediate_analyse_cicd_repo

## Périmètre — § 13

Cartographier le repo partagé `ci-cd-unified-template-v1.0` :
- Arborescence (§ 13.1) — `templates/`, `deploy/scripts/`, `deploy/helm/api-chart/`, `lint/`, `examples/minimal-project/`, `tests/`
- Versioning Semver via tags Git (§ 13.2)
- Tests automatisés (§ 13.3) — shellcheck, helm lint, intégration
- Règles de contribution (§ 13.4)
- Anti-patterns (§ 13.5)

## Base skills (parallélisables)

- `dx_base_analyse_cicd_repo_tree` — l'arborescence existe-t-elle ?
- `dx_base_analyse_cicd_repo_parent_yml` — `templates/parent.yml` présent et bien structuré ?
- `dx_base_analyse_cicd_repo_child_stages` — stages test/build/deploy/smoke-test/rollback présents ?
- `dx_base_analyse_cicd_repo_helm_chart` — `api-chart/` complet (Chart.yaml, values.yaml, values.schema.json, templates/) ?
- `dx_base_analyse_cicd_repo_scripts` — scripts deploy-api.sh, smoke-test.sh, migrate_with_lease.py, resolve-kubeconfig.sh présents ?
- `dx_base_analyse_cicd_repo_lint_templates` — importlinter-template.toml, eslintrc-template.js, .trivyignore présents ?
- `dx_base_analyse_cicd_repo_examples` — `examples/minimal-project/` aligné avec le chart courant ?
- `dx_base_analyse_cicd_repo_tests` — `tests/shellcheck/`, `tests/helm/`, `tests/pipeline/` présents ?
- `dx_base_analyse_cicd_repo_semver_tags` — tags Git suivent vMAJOR.MINOR.PATCH ?
- `dx_base_analyse_cicd_repo_changelog` — CHANGELOG.md à jour avec sections "Breaking changes" pour les MAJOR ?
- `dx_base_analyse_cicd_repo_no_project_specifics` — pas de logique projet-spécifique ?

## Format de sortie

- Arborescence relevée vs attendue (diff)
- Liste des fichiers manquants ou supplémentaires non documentés
- Couverture tests par catégorie
- Dernier tag Semver + écart depuis HEAD
- Anti-patterns détectés (§ 13.5)

## Anti-patterns à signaler

1. Logique projet-spécifique dans le repo partagé
2. Breaking change publié en MINOR/PATCH
3. Tests absents → bugs visibles uniquement chez les consommateurs
4. `examples/` désynchronisé du chart
5. Scripts sans `shellcheck`
