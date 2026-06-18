# Matrice de validation de conformité v1.4

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Source de vérité: `docs/regles-architecture-deploiement.md`
Skills: `.agents/skills/`, version `v1.7.0`

## Légende

| Statut | Sens |
|---|---|
| OK | Conforme avec preuve vérifiée |
| VIOLATION | Non conforme, correction requise |
| A_VERIFIER | Pas assez de preuve |
| N/A | Non applicable à CDE |
| BLOQUE | Validation impossible sans accès externe ou décision |

Criticité: `critique` si la règle bloque sécurité, déploiement, rollback ou isolation; `à corriger` sinon.

## Matrice maître

| ID | Section | Domaine | Skill de validation | Preuve attendue | Statut initial | Criticité |
|---|---:|---|---|---|---|---|
| M-00 | § 10.3-10.4 | Source de vérité et skills | `dx_intermediate_check_project_conventions` | `AGENTS.md`, `.agents/skills/`, `.agents/update-skills.sh`, `.agents/.skills-version` | OK | critique |
| M-01 | § 2, § 8.1 | Architecture APIs deux tiers | `dx_intermediate_check_apis` | Arborescence `apis/exposed`, `apis/internal`, absence DB dans B4F, absence backend dans gateway | A_VERIFIER | critique |
| M-02 | § 2.7 | Alembic et DB | `dx_intermediate_check_apis` + base Alembic | Aucune DDL runtime, migrations avec schema + downgrade testé | VIOLATION | critique |
| M-03 | § 3, § 14 | Frontend Angular/NGRX | `dx_intermediate_check_frontend_ngrx`, `dx_intermediate_check_frontend_clean_archi` | Store feature par B4F, HTTP dans Effects, modèles domaine | VIOLATION | à corriger |
| M-04 | § 4, § 8.3 | CI/CD | `dx_intermediate_check_cicd_pipeline` | `.gitlab-ci.yml` minimal, parent/child, 5 stages, Harbor verify, pas de migrate stage | VIOLATION | critique |
| M-05 | § 5, § 8.4 | Kubernetes et gateway | `dx_intermediate_check_k8s_config` | Gateway unique, Backends internes, initContainer migrate, Lease RBAC | VIOLATION | critique |
| M-06 | § 6, § 8.5 | Variables d'environnement | `dx_intermediate_check_env_vars` | Variables scopées GitLab, pas de préfixes DEV/STAGING/PROD, `.env.example` | A_VERIFIER | critique |
| M-07 | § 7, § 8.6 | Harbor registry | `dx_intermediate_check_registry_to_k8s` | Harbor robot, imagePullSecrets, Cosign, absence `CI_REGISTRY_*` | A_VERIFIER | critique |
| M-08 | § 5.8-5.10, § 8.8 | Observabilité et probes | `dx_intermediate_check_k8s_config` | `/liveness`, `/readiness`, `/startup`, `/health`, `/metrics`, logs JSON, trace_id | A_VERIFIER | critique |
| M-09 | § 10, § 11 | Conventions et dev local | `dx_intermediate_check_local_dev` | Wrappers racine, scripts par API, compose postgres/pgbouncer/redis/alloy | VIOLATION | à corriger |
| M-10 | § 12 | Clean Architecture API | `dx_intermediate_check_clean_archi_apis` | `domain/application/infrastructure/presentation`, import-linter, tests par couche | A_VERIFIER | à corriger |
| M-11 | § 9 | Rapport final | `dx_master_check` | Rapport markdown avec violations, résumé et variables CI/CD | A_VERIFIER | critique |

## Matrice détaillée

### 1. Source de vérité et outillage portable

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| S-01 | `docs/regles-architecture-deploiement.md` est versionné | § 1, § 10.1 | `dx_base_check_agent_rules_single_source` | Vérifier le fichier et les références dans `AGENTS.md` | OK | `docs/regles-architecture-deploiement.md` présent |
| S-02 | `AGENTS.md` existe à la racine | § 10.3 | `dx_base_check_agents_md_present` | `[ -f AGENTS.md ]` | OK | `AGENTS.md` présent |
| S-03 | `.agents/skills/` est présent et versionné | § 10.3-10.4 | `dx_base_check_agents_dir_present` | `[ -d .agents/skills ]` + `find .agents/skills -name SKILL.md` | OK | 204 skills validées |
| S-04 | `update-skills.sh` présent | § 10.4 | `dx_base_check_update_skills_script_present` | `[ -x .agents/update-skills.sh ]` | OK | `.agents/update-skills.sh` présent |
| S-05 | Version des skills traçable | § 10.4 | `dx_base_check_skills_version_tracked` | Lire `.agents/.skills-version` | OK | `v1.7.0` |
| S-06 | Aucun dossier/fichier outil spécifique interdit | § 10.3 | `dx_base_check_no_tool_specific_dirs` | `find` des patterns interdits | OK | `.kilo/` supprimé |
| S-07 | Aucun `SKILL.md` local modifié manuellement | § 10.4 | `dx_base_check_skills_not_modified_locally` | Comparer au repo central/tag | A_VERIFIER | À revalider avant commit |

### 2. Architecture APIs

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| A-01 | B4F sous `apis/exposed/`, Backends sous `apis/internal/` | § 2.1 | `dx_base_check_api_tier_placement` | `find apis/exposed apis/internal` | OK | Structure présente |
| A-02 | Aucune B4F avec DB/Alembic/`DATABASE_URL` | § 2.2 | `dx_base_check_api_no_db_in_b4f` | Recherche `alembic`, `DATABASE_URL`, SQLAlchemy dans `apis/exposed` | A_VERIFIER | Audit à compléter |
| A-03 | Aucun Backend dans le gateway | § 2.3, § 5.11 | `dx_base_check_api_no_backend_in_ingress` | Lire gateway values/templates | VIOLATION | `gateway-chart/templates/ingress.yaml` contient `apiRoutes.apis` |
| A-04 | Frontend ne cible que les B4F | § 2.9 | `dx_base_check_api_no_frontend_to_backend` | Recherche `backend-api` dans `frontend/` | A_VERIFIER | Audit à compléter |
| A-05 | Aucun HTTP Backend->Backend | § 2.4 | `dx_base_check_api_no_http_between_backends` | Recherche clients HTTP dans `apis/internal` | A_VERIFIER | Plusieurs `httpx` à classifier |
| A-06 | B4F porte logique métier, pas proxy CRUD 1:1 | § 2.2, § 2.8 | `dx_base_check_b4f_holds_business_logic` | Lire routes B4F et clients backend | VIOLATION | Plusieurs routes documentées comme proxy |
| A-07 | Backend possède une entité principale atomique | § 2.3 | `dx_base_check_backend_atomic_entity` | Cartographier modèles par backend | A_VERIFIER | Audit à compléter |
| A-08 | Services externes seulement côté Backend | § 2.2-2.3 | `dx_base_check_backend_owns_infrastructure` | Recherche clients MS365/Membrane dans B4F | VIOLATION | `communication-b4f-api` contient des appels externes |
| A-09 | Redis event bus présent | § 2.4 | `dx_base_check_api_event_bus_redis` | Vérifier `REDIS_URL`, compose, Helm, publishers/subscribers | A_VERIFIER | Redis présent dans compose, Helm à valider |

### 3. Alembic et base de données

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| DB-01 | Aucune DDL au startup | § 2.7.5 | `dx_base_check_alembic_no_create_all_in_code` | `rg "create_all|db.create_all|DDL"` | OK | `rg "metadata\\.create_all|db\\.create_all|SQLModel\\.metadata\\.create_all|drop_all\\(" apis -g '*.py'` ne retourne aucune DDL runtime |
| DB-02 | Toute DDL passe par Alembic | § 2.7.5 | `dx_base_check_alembic_all_ddl_in_alembic` | Chercher `.sql`, `CREATE TABLE`, `CREATE SCHEMA` hors versions | A_VERIFIER | Audit à compléter |
| DB-03 | Première migration crée le schéma du service | § 2.7.2, § 2.7.5 | `dx_base_check_alembic_first_revision_creates_schema` | Lire première révision par backend | A_VERIFIER | Audit à compléter |
| DB-04 | Downgrade non vide | § 2.7.5 | `dx_base_check_alembic_downgrade_not_empty` | `rg "def downgrade|pass|NotImplementedError"` | A_VERIFIER | Fonctions présentes, contenu à valider |
| DB-05 | Downgrade symétrique | § 2.7.5 | `dx_base_check_alembic_downgrade_symmetric` | Comparer opérations upgrade/downgrade | A_VERIFIER | Audit manuel requis |
| DB-06 | CI teste downgrade puis upgrade | § 2.7.5, § 4.9 | `dx_base_check_alembic_ci_tests_downgrade` | Lire `.gitlab-ci.yml` / template child | OK | Les 11 `apis/internal/*-backend-api/run_tests.sh` exécutent `alembic upgrade head`, `alembic downgrade -1`, puis `alembic upgrade head`; le child pipeline appelle `run_tests.sh` quand présent |
| DB-07 | InitContainer exécute `scripts/migrate_with_lease.py` | § 2.7.5 | `dx_base_check_api_migration_initcontainer` | Lire deployment chart/values | VIOLATION | InitContainer absent |
| DB-08 | Lease Kubernetes et RBAC présents | § 2.7.5 | `dx_base_check_api_migration_lease` | Chercher `coordination.k8s.io`, `leases` | VIOLATION | RBAC absent |
| DB-09 | Pool SQLAlchemy compatible PgBouncer | § 2.7.3-2.7.4 | `dx_base_check_api_db_pool_size` | Lire `apis/shared/database` | A_VERIFIER | Audit à compléter |

### 4. CI/CD

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| CI-01 | `.gitlab-ci.yml` inclut seulement le repo partagé v1.0 | § 4.1 | `dx_base_check_cicd_canonical_includes` | Lire `include:` | VIOLATION | Inclut `infrastructure/ci-templates` |
| CI-02 | Includes taggés, jamais `main` | § 4.1, § 4.12 | `dx_base_check_cicd_include_tag_version` | Lire `ref:` | VIOLATION | `ref: main` |
| CI-03 | Parent/child et 5 stages seulement | § 4.2 | `dx_base_check_cicd_five_stages_only` | Lire `stages:` | VIOLATION | Stages multiples dont migrate/rollback par env |
| CI-04 | Aucun stage de migration | § 4.2, § 4.12 | `dx_base_check_cicd_no_migration_stage` | Chercher `migrate-` | VIOLATION | `migrate-dev/staging/prod` présents |
| CI-05 | Aucun `allow_failure: true` | § 4.9 | `dx_base_check_cicd_no_allow_failure` | `rg "allow_failure"` | VIOLATION | Frontend test en allow_failure |
| CI-06 | Couverture 85 %, JUnit, Cobertura | § 4.9 | `dx_base_check_cicd_coverage_85_percent` | Lire jobs test | VIOLATION | Les 11 scripts backend imposent `--cov-fail-under=85`, `coverage.xml` et `junit.xml`; les B4F et la CI globale restent à aligner |
| CI-07 | Kaniko + Harbor, pas Docker-in-Docker | § 4.10 | `dx_base_check_cicd_kaniko_build` | Lire build jobs | A_VERIFIER | Kaniko présent mais repo include legacy |
| CI-08 | Job `verify:<api>` Harbor/Cosign | § 4.10 | `dx_base_check_cicd_verify_job` | Lire child pipeline/template | VIOLATION | Non visible dans CI actuelle |
| CI-09 | Pas de déploiement auto staging/prod | § 4.3 | `dx_base_check_cicd_no_auto_deploy_staging_prod` | Lire rules deploy staging/prod | A_VERIFIER | Audit à compléter |
| CI-10 | Projet values-only, pas de scripts/charts partagés locaux | § 4.1, § 8.3 | `dx_base_check_cicd_no_deploy_scripts_in_project` | `find deploy/helm deploy/scripts` | VIOLATION | `deploy/helm` et `deploy/scripts` présents |

### 5. Kubernetes et gateway

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| K-01 | Envs canoniques `dev/staging/prod` | § 5.1 | `dx_base_check_k8s_env_names_canonical` | Lire deploy values/CI | OK | Dossiers values dev/staging/prod |
| K-02 | `NAMESPACE` non hardcodé | § 5.3 | `dx_base_check_k8s_namespace_from_variable` | Lire CI/scripts | VIOLATION | `cde-dev` hardcodé dans CI |
| K-03 | `KUBECONFIG_VARIABLE`, pas variable directe | § 5.4 | `dx_base_check_k8s_kubeconfig_indirection` | Lire CI | VIOLATION | `CROO_KUBECONFIG` direct |
| K-04 | Gateway unique par namespace | § 5.11 | `dx_base_check_gateway_chart_exists` | Lire charts/ingress | A_VERIFIER | Chart présent, conformité à valider |
| K-05 | Gateway route `/` vers frontend | § 5.11-5.12 | `dx_base_check_gateway_routes_frontend_root` | Lire ingress | OK | `frontendRoute` présent |
| K-06 | Gateway route `/api/<service>/v1` vers B4F seulement | § 5.11 | `dx_base_check_gateway_routes_apis_under_api_prefix` | Lire `apiRoutes` | VIOLATION | `apiRoutes.apis` peut exposer backends |
| K-07 | HTTPS redirect et wildcard TLS | § 5.7, § 5.11 | `dx_base_check_gateway_uses_wildcard_tls` | Lire values/annotations | A_VERIFIER | Audit à compléter |
| K-08 | Probes health non authentifiées | § 5.10 | `dx_base_check_k8s_health_endpoints` | Appeler/lire routes API | A_VERIFIER | Audit à compléter |

### 6. Registry Harbor

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| R-01 | Harbor registry primaire | § 7.1 | `dx_base_check_registry_harbor_primary` | Lire CI variables/templates | A_VERIFIER | Dépend du template cible |
| R-02 | Robot account Harbor | § 7.2-7.3 | `dx_base_check_registry_robot_account` | Vérifier variables GitLab | BLOQUE | Nécessite accès GitLab variables |
| R-03 | Aucun `CI_REGISTRY_*` / `DEPLOY_TOKEN_*` | § 7.3, § 8.6 | `dx_base_check_registry_harbor_primary` | `rg "CI_REGISTRY|DEPLOY_TOKEN"` | A_VERIFIER | Audit à compléter |
| R-04 | `imagePullSecrets` et ServiceAccount | § 7.7 | `dx_base_check_registry_imagepullsecrets` | Lire chart/values | A_VERIFIER | Audit à compléter |
| R-05 | Verify Harbor + Cosign | § 4.10, § 7.7 | `dx_base_check_cicd_verify_job` | Lire pipeline/template | VIOLATION | Non visible dans CI actuelle |

### 7. Frontend

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| F-01 | Un service Angular par B4F | § 3.1 | `dx_base_check_frontend_ngrx_service_per_b4f` | Mapper services vers B4F | A_VERIFIER | Plusieurs `shared/services` présents |
| F-02 | Un feature NGRX par B4F | § 3.1 | `dx_base_check_frontend_ngrx_feature_per_b4f` | Chercher `store/<feature>` | VIOLATION | Store feature absent ou incomplet |
| F-03 | Aucun HTTP hors Effects | § 3.1-3.6 | `dx_base_check_frontend_ngrx_no_http_outside_effects` | Recherche `HttpClient`/services dans components | A_VERIFIER | Audit à compléter |
| F-04 | Templates utilisent `| async` | § 3.1 | `dx_base_check_frontend_ngrx_template_uses_async` | Lire templates critiques | A_VERIFIER | Audit à compléter |
| F-05 | API base URL = `/api` | § 5.12 | `dx_base_check_frontend_api_base_url_is_api` | Lire environments | A_VERIFIER | Audit à compléter |
| F-06 | Playwright E2E sous `frontend/e2e/` | § 3.8 | `dx_base_check_frontend_e2e_in_e2e_dir` | `find frontend/e2e` | A_VERIFIER | Audit à compléter |
| F-07 | E2E absent du pipeline CI | § 3.8 | `dx_base_check_frontend_e2e_not_in_ci` | Lire `.gitlab-ci.yml` | A_VERIFIER | Audit à compléter |
| F-08 | Hook pre-commit smoke E2E | § 3.8 | `dx_base_check_frontend_pre_commit_hook` | Lire package/husky/scripts | A_VERIFIER | Audit à compléter |

### 8. Observabilité

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| O-01 | Logs JSON stdout/stderr | § 5.8 | `dx_base_check_k8s_logs_stdout_json` | Lire logging shared | A_VERIFIER | Audit à compléter |
| O-02 | `/metrics` sur chaque API | § 5.8, § 5.10 | `dx_base_check_k8s_metrics_endpoint` | Lire routes / appeler local | A_VERIFIER | Audit à compléter |
| O-03 | OTel vers Alloy | § 5.8 | `dx_base_check_k8s_observability_alloy_otlp` | Lire env/compose/chart | A_VERIFIER | Compose à compléter avec Alloy |
| O-04 | Propagation `traceparent` | § 5.9 | `dx_base_check_k8s_traceparent_propagation` | Lire HTTP client/middleware | A_VERIFIER | Audit à compléter |
| O-05 | `trace_id` dans events Redis | § 2.4, § 5.9 | `dx_base_check_k8s_trace_id_in_events` | Lire schemas event bus | A_VERIFIER | Audit à compléter |
| O-06 | `/health` liste dépendances | § 5.10 | `dx_base_check_k8s_health_endpoints` | Lire routes / appeler local | A_VERIFIER | Audit à compléter |

### 9. Développement local et conventions

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| L-01 | Wrappers racine présents | § 11.1 | `dx_base_check_local_dev_root_wrappers` | `ls run_* migrate_all_apis.sh` | A_VERIFIER | Certains scripts présents à vérifier |
| L-02 | Scripts par API uniformes | § 11.2 | `dx_base_check_local_dev_per_api_scripts` | `find apis -name run_api.sh -o -name run_tests.sh` | A_VERIFIER | Les 11 scripts backend `run_tests.sh` sont uniformisés; les scripts B4F restent à aligner |
| L-03 | B4F sans `migrate.sh` | § 11.2 | `dx_base_check_apis_uniform_scripts` | `find apis/exposed -name migrate.sh` | A_VERIFIER | Audit à compléter |
| L-04 | Compose postgres + pgbouncer + redis + alloy | § 11.3 | `dx_base_check_local_dev_docker_compose` | Lire `docker-compose.yml` | VIOLATION | PgBouncer/Alloy à confirmer/ajouter |
| L-05 | `.env.example` à jour | § 11.4 | `dx_base_check_local_dev_env_example` | `[ -f .env.example ]` + variables | A_VERIFIER | Audit à compléter |
| L-06 | Docs sous `/docs` | § 10.1 | `dx_base_check_conventions_repo_structure` | Chercher docs hors racine autorisée | A_VERIFIER | `Cameleon/` est plan de travail, décider destination finale |
| L-07 | Pas de données client réelles | § 10.2 | `dx_base_check_env_vars_no_secret_in_repo` | Scan secrets/data | A_VERIFIER | Audit à compléter |

### 10. Clean Architecture

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| CA-01 | APIs en 4 couches uniformes | § 12.2 | `dx_intermediate_check_clean_archi_apis` | `find apis -maxdepth` + import graph | A_VERIFIER | Structure partiellement présente |
| CA-02 | `domain/` sans framework | § 12.3 | `dx_intermediate_check_clean_archi_apis` | Recherche imports FastAPI/SQLAlchemy/Pydantic dans domain | A_VERIFIER | Audit à compléter |
| CA-03 | `application/` sans framework | § 12.3 | `dx_intermediate_check_clean_archi_apis` | Recherche imports FastAPI/SQLAlchemy/Pydantic dans application | A_VERIFIER | Audit à compléter |
| CA-04 | Routes sans logique métier | § 12.3 | `dx_intermediate_check_clean_archi_apis` | Lire routes longues/complexes | A_VERIFIER | Audit à compléter |
| CA-05 | Entités métier ne dérivent pas de SQLAlchemy/Pydantic | § 12.3 | `dx_intermediate_check_clean_archi_apis` | Recherche `Base`, `BaseModel` dans domain entities | A_VERIFIER | Audit à compléter |
| CA-06 | Import-linter configuré | § 12.3 | `dx_intermediate_check_clean_archi_apis` | Lire config test/lint | A_VERIFIER | Audit à compléter |

## Commandes de validation recommandées

```bash
# Skills
tmpdir=$(mktemp -d)
git clone --depth 1 --branch "$(cat .agents/.skills-version)" git@gitlab.tools.thesmartcrew.com:croo-dev/code-agent-skills-v1.0.git "$tmpdir/skills"
bash "$tmpdir/skills/scripts/validate-skills.sh" .agents/skills
rm -rf "$tmpdir"

# Source/règles/outillage
test -f AGENTS.md
test -d .agents/skills
test -x .agents/update-skills.sh
find . -maxdepth 3 \( -name '.kilo*' -o -name '.cursor*' -o -name '.claude*' -o -name '.aider*' -o -name '.continue*' -o -name '.windsurf*' -o -name '.codeium*' -o -name '.copilot*' -o -name 'CLAUDE.md' \) -not -path './.git/*'

# Violations connues
rg "create_all|db.create_all|SQLModel.metadata.create_all" apis
rg "migrate-dev|migrate-staging|migrate-prod|allow_failure|infrastructure/ci-templates|ref: main" .gitlab-ci.yml
rg "apiRoutes\.apis|backend-api" deploy/helm/gateway-chart deploy/helm/values frontend/src/app

# Matrice / rapport
# Utiliser dx_master_check pour produire le rapport final au format § 9.
```

## Critères de sortie

- Tous les `VIOLATION` critiques passent à `OK` ou `BLOQUE` avec justification vérifiable.
- Aucun `A_VERIFIER` ne reste avant la MR finale.
- Le rapport § 9 est produit avec les fichiers/lignes de preuve.
- Les captures UI sont présentes dans `captures/` quand le frontend est touché.
