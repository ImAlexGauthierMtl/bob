---
name: dx_intermediate_analyse_cicd_pipeline
description: Analyse le pipeline CI/CD GitLab d'un projet (parent + child, 5 stages, build Kaniko vers Harbor, verify Harbor+Cosign, smoke-test, déploiement Helm) selon le chapitre 4. Inventaire des stages, jobs, scripts inline, dépendances au repo central ci-cd-unified-template-v1.0. À invoquer pour comprendre comment le pipeline est structuré, repérer la logique dupliquée hors du repo central, les stages exotiques, les déploiements auto sur staging/prod.
metadata:
  reference: § 4 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_analyse_cicd_pipeline

## Périmètre

Examiner :
- `.gitlab-ci.yml` du projet — doit contenir uniquement des `include:` vers le repo central
- ref de l'include (jamais `main`, toujours un tag versionné)
- structure parent (stage `discover`) / child (5 stages : test, build, deploy, smoke-test, rollback)
- `deploy/values/{env}/<api>.yaml` présents pour chaque API × environnement
- absence de `deploy/scripts/` ou `deploy/helm/templates/` côté projet (ils doivent vivre dans le repo central)
- déclencheurs : push main → dev auto, MR → review auto, tag v* → staging/prod manuel
- stage `build` utilise Kaniko (pas docker-in-docker)
- verify Harbor en job séparé `verify:<api>` avec `needs: [build:<api>]`
- stage `smoke-test` qui vérifie /liveness, /readiness, /startup, /metrics, /health
- couverture 85 % enforced + reports JUnit + Cobertura
- `CICD_MAX_PARALLEL_JOBS` respecté

## Base skills (parallélisables)

- `dx_base_check_cicd_only_includes_from_shared`
- `dx_base_check_cicd_no_deploy_scripts_in_project`
- `dx_base_check_cicd_include_tag_version`
- `dx_base_check_cicd_values_per_env_per_api`
- `dx_base_check_cicd_5_stages_only`
- `dx_base_check_cicd_kaniko_build`
- `dx_base_check_cicd_verify_job`
- `dx_base_check_cicd_smoke_test_endpoints`
- `dx_base_check_cicd_coverage_85_percent`

## Format de sortie

```markdown
## Analyse Pipeline CI/CD (§ 4)

### Structure
- .gitlab-ci.yml du projet : N lignes, contient `include:` vers <ref>
- Stages du child : ...
- Tag d'image utilisé : <SHA / v* / latest>

### Déclencheurs
- Push main : ...
- MR : ...
- Tag v* : ...

### Qualité
- Build outil : Kaniko / docker:dind / autre
- Job verify (scan Harbor + signature Cosign) : présent / absent / ne bloque pas HIGH-CRITICAL
- Smoke-test : présent / absent / endpoints couverts : ...
- Couverture : seuil X %, reports JUnit/Cobertura présents ?
```
