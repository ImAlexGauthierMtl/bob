---
name: dx_intermediate_check_cicd_repo
description: Vérifie pass/fail la conformité du repo CI/CD partagé (ci-cd-unified-template-v1.0) au chapitre 13. À invoquer dans la pipeline du repo partagé lui-même, ou en audit ponctuel. Vérifie arborescence, Semver, tests automatisés, contribution, anti-patterns. Couvre la section 8.8 implicite (audit du repo partagé).
metadata:
  reference: § 13 de docs/architecture/regles-architecture-deploiement.md
  target_repo: git@gitlab.tools.thesmartcrew.com:croo-dev/ci-cd-unified-template-v1.0.git
---

# dx_intermediate_check_cicd_repo

## Périmètre — § 13

Checklist :

```
- [ ] README.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE présents
- [ ] docs/usage.md, docs/upgrade-guide.md, docs/architecture.md présents
- [ ] templates/parent.yml présent (importé par les projets)
- [ ] templates/child/stages/ : test, build, deploy, smoke-test, rollback
- [ ] templates/child/jobs/ : provision-registry-access, discover-apis
- [ ] deploy/scripts/ : discover-apis.sh, deploy-api.sh, smoke-test.sh, rollback-api.sh
- [ ] deploy/scripts/migrate_with_lease.py présent (Lease Kubernetes)
- [ ] deploy/scripts/resolve-kubeconfig.sh, resolve-tls.sh présents
- [ ] deploy/scripts/lib/helpers.sh, env.sh présents
- [ ] deploy/helm/api-chart/Chart.yaml, values.yaml, values.schema.json présents
- [ ] api-chart/templates/ : deployment, service, ingress, serviceaccount, certificate, _helpers
- [ ] lint/importlinter-template.toml, lint/eslintrc-template.js, lint/harbor-cve-whitelist.yaml
- [ ] examples/minimal-project/ aligné avec api-chart courant
- [ ] tests/shellcheck/, tests/helm/, tests/pipeline/ existent et tournent en pipeline
- [ ] .gitlab-ci.yml du repo partagé applique : shellcheck, helm lint/template, validate YAML
- [ ] Couverture 85 % sur scripts Python (migrate_with_lease.py)
- [ ] Tags Git suivent vMAJOR.MINOR.PATCH
- [ ] CHANGELOG.md à jour, section "Breaking changes" présente pour chaque MAJOR
- [ ] Aucun breaking change en MINOR/PATCH (audit des derniers commits)
- [ ] Période de support : dernière MAJOR + avant-dernière supportées en parallèle
- [ ] Warnings de deprecation visibles dans les logs avant suppression
- [ ] Aucune logique projet-spécifique (grep contre noms de projets connus)
```

## Base skills (parallélisables)

- `dx_base_check_cicd_repo_required_files`
- `dx_base_check_cicd_repo_template_stages_complete`
- `dx_base_check_cicd_repo_helm_chart_complete`
- `dx_base_check_cicd_repo_scripts_complete`
- `dx_base_check_cicd_repo_lint_templates_complete`
- `dx_base_check_cicd_repo_examples_sync_with_chart`
- `dx_base_check_cicd_repo_tests_present`
- `dx_base_check_cicd_repo_semver_tags`
- `dx_base_check_cicd_repo_changelog_breaking_for_major`
- `dx_base_check_cicd_repo_no_project_specifics`
- `dx_base_check_cicd_repo_shellcheck_clean`
- `dx_base_check_cicd_repo_helm_lint_clean`

## Format de sortie

Tableau pass/fail (format § 9). Si exécuté **dans** le repo partagé, échouer la pipeline en cas de FAIL.
