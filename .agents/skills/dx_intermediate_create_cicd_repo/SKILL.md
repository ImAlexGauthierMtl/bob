---
name: dx_intermediate_create_cicd_repo
description: Bootstrap ou complète le repo CI/CD partagé (ci-cd-unified-template-v1.0) selon le chapitre 13. À invoquer pour créer la structure depuis zéro ou ajouter des éléments manquants (chart Helm, scripts deploy, examples/, tests/). Crée parent.yml, child stages, api-chart, scripts, exemples, tests et la pipeline du repo lui-même.
metadata:
  reference: § 13 de docs/architecture/regles-architecture-deploiement.md
  target_repo: git@gitlab.tools.thesmartcrew.com:croo-dev/ci-cd-unified-template-v1.0.git
---

# dx_intermediate_create_cicd_repo

## Périmètre

Créer ou compléter l'arborescence du repo partagé :

```
cicd-templates/
├── README.md, CHANGELOG.md, CONTRIBUTING.md, LICENSE
├── docs/{usage,upgrade-guide,architecture}.md
├── templates/parent.yml
├── templates/child/stages/{test,build,deploy,smoke-test,rollback}.yml
├── templates/child/jobs/{provision-registry-access,discover-apis}.yml
├── deploy/scripts/{discover-apis,deploy-api,smoke-test,rollback-api}.sh
├── deploy/scripts/migrate_with_lease.py
├── deploy/scripts/{resolve-kubeconfig,resolve-tls}.sh
├── deploy/scripts/lib/{helpers,env}.sh
├── deploy/helm/api-chart/{Chart.yaml,values.yaml,values.schema.json}
├── deploy/helm/api-chart/templates/{deployment,service,ingress,serviceaccount,certificate,networkpolicy,_helpers}.yaml
├── lint/{importlinter-template.toml,eslintrc-template.js,harbor-cve-whitelist.yaml}
├── examples/minimal-project/
├── tests/{shellcheck,helm,pipeline}/
└── .gitlab-ci.yml
```

## Base skills (séquence)

1. `dx_base_create_cicd_repo_root_files` (README, CHANGELOG, CONTRIBUTING, LICENSE) — //
2. `dx_base_create_cicd_repo_docs` (3 fichiers docs) — //
3. `dx_base_create_cicd_repo_parent_template` (parent.yml + child stages) — //
4. **api-chart** : `dx_base_create_cicd_repo_helm_chart` (Deployment + Service ClusterIP + initContainer migrate + probes + OTel ; PAS d'Ingress, PAS de certificate)
5. **frontend-chart** : `dx_base_create_frontend_chart` (Deployment + Service ClusterIP + probes statiques)
6. **gateway-chart** : `dx_base_create_gateway_chart` (Ingress unique + cert-copy Job + RBAC minimal)
7. `dx_base_create_cicd_repo_scripts` (migrate_with_lease.py, discover-apis.sh, resolve-kubeconfig.sh, deploy-api.sh **sans TLS**)
8. `dx_base_create_deploy_frontend_script`
9. `dx_base_create_deploy_gateway_script` (scan apis/exposed/, helm upgrade gateway en dernier)
10. `dx_base_create_cicd_repo_lint_templates`
11. `dx_base_create_cicd_repo_examples` (avec values frontend.yaml + gateway.yaml par env)
12. `dx_base_create_cicd_repo_tests_pipeline`
13. `dx_base_create_cicd_repo_self_ci` (.gitlab-ci.yml du repo partagé : shellcheck + helm lint sur les 3 charts + YAML validate + coverage Python)

## Principes guidants

- **Aucune logique projet-spécifique** : tout est paramétrable via variables CI ou values Helm
- **Trois charts paritaires** : api-chart, frontend-chart, gateway-chart
- **Un seul Ingress par namespace** : le gateway (§ 5.11)
- **TLS unique** : un wildcard copié depuis cert-manager namespace
- **HTTPS forcé** : annotations ssl-redirect + force-ssl-redirect non négociables
- **Semver via tags** : v1.0.0 initial après le premier passage de tous les tests
- **Tests visibles dans la pipeline du repo lui-même** — pas dans les consommateurs
- **examples/minimal-project/** consommé par les tests d'intégration → garantit qu'il reste synchronisé

## Format de sortie

Liste des fichiers créés, tag Semver initial proposé, commande de validation locale (`shellcheck deploy/scripts/*.sh && helm lint deploy/helm/api-chart`).
