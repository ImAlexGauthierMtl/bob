---
name: dx_intermediate_check_cicd_pipeline
description: Verdict pass/fail du pipeline CI/CD selon § 4 et § 8.3. Couvre les 2 file-includes du repo central, les 5 stages exclusifs, build Kaniko vers Harbor, verify (scan Harbor + Cosign), smoke-test, déclencheurs, tags d'image, couverture 85 %, JUnit + Cobertura, absence d'allow_failure, déploiement manuel staging/prod.
metadata:
  reference: § 4 + § 8.3 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_check_cicd_pipeline

## Périmètre — § 8.3

Vérifier toutes les cases de § 8.3 (≈30 items). Points critiques :
- `include:` versionné par tag (jamais `main`)
- Aucun `/deploy/scripts/` ni `/deploy/helm/templates/` côté projet
- 5 stages exclusifs : test, build, deploy, smoke-test, rollback
- Aucun stage de migration séparé
- Build avec **Kaniko** (jamais `docker:24-dind`)
- Job `scan:<api>` séparé avec `needs: [build:<api>]`, `--exit-code 1` sur HIGH/CRITICAL
- `.trivyignore` au repo partagé, exceptions datées
- Smoke-test vérifie présence de `/liveness`, `/readiness`, `/startup`, `/metrics`, `/health` + dépendances
- Couverture 85 % enforced + JUnit + Cobertura + regex coverage
- Aucun `allow_failure: true`
- Aucun tag `latest` ni mutable
- Aucun déploiement automatique sur staging/prod
- `artifacts:when: always`
- Pas de noms d'API ni de projet hardcodés

## Base skills (parallélisables)

- `dx_base_check_cicd_only_includes_from_shared`
- `dx_base_check_cicd_include_tag_version`
- `dx_base_check_cicd_no_deploy_scripts_in_project`
- `dx_base_check_cicd_values_per_env_per_api`
- `dx_base_check_cicd_5_stages_only`
- `dx_base_check_cicd_no_migration_stage`
- `dx_base_check_cicd_no_allow_failure`
- `dx_base_check_cicd_coverage_85_percent`
- `dx_base_check_cicd_junit_cobertura_reports`
- `dx_base_check_cicd_artifacts_always`
- `dx_base_check_cicd_coverage_regex`
- `dx_base_check_cicd_kaniko_build`
- `dx_base_check_cicd_verify_job`
- `dx_base_check_cicd_harbor_cve_whitelist`
- `dx_base_check_cicd_smoke_test_endpoints`
- `dx_base_check_cicd_smoke_test_dependencies`
- `dx_base_check_cicd_image_tag_strategy`
- `dx_base_check_cicd_no_auto_deploy_staging_prod`
- `dx_base_check_cicd_no_latest_tag`
- `dx_base_check_cicd_no_hardcoded_api_names`
- `dx_base_check_cicd_concurrency_resource_group`

### Consolidation v1.2 — un seul include côté projet

- `dx_base_check_cicd_canonical_includes` — exactement 1 include, pointant sur croo-dev/ci-cd-unified-template-v1.0
- `dx_base_check_cicd_canonical_includes` — kaniko.yml chargé via parent.yml (pas à dupliquer)
- `dx_base_check_cicd_kaniko_image_harbor` — KANIKO_IMAGE sur le bon registry path
- `dx_base_check_cicd_no_legacy_repo_references` — aucun `infrastructure/ci-templates`, `shared/cicd-templates`, `gitlab.example.com`

## Format

Standard § 9.
