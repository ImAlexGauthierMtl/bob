# Plan de refactor CDE vers les normes v1.4

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Source de vérité: `docs/regles-architecture-deploiement.md`
Skills: `.agents/skills/` depuis `croo-dev/code-agent-skills-v1.0`, version `v1.7.0`
Matrice de contrôle: `Cameleon/matrice-validation-conformite-v1.4.md`

## Objectif

Refactorer CDE vers les règles d'architecture et déploiement v1.4. Le plan suit le document officiel: modèle API deux tiers, frontend Angular/NGRX, CI/CD parent-child via le repo partagé, Kubernetes/gateway, variables, Harbor, conventions projet, observabilité, développement local, Clean Architecture et validation finale au format § 9.

## Principes d'exécution

- Utiliser `docs/regles-architecture-deploiement.md` comme source de vérité unique.
- Utiliser les skills `dx_*` comme guides d'analyse, de création et de check.
- Ne pas recréer d'ancien framework local; conserver seulement `.agents/skills/`, `.agents/update-skills.sh`, `.agents/.skills-version` et `AGENTS.md`.
- Piloter chaque MR avec la matrice de conformité: une règle corrigée doit avoir une preuve, une commande ou un fichier témoin.
- Ne pas mélanger refactor structurel et refactor fonctionnel sans preuve de non-régression.

## État initial CDE

### Déjà aligné partiellement

- APIs séparées en `apis/exposed/` et `apis/internal/`.
- Backends internes avec dossiers Alembic.
- Frontend isolé dans `frontend/`.
- Présence d'un gateway chart, d'un frontend chart et d'un api chart, à migrer vers le modèle repo partagé.
- `docker-compose.yml` contient PostgreSQL et Redis, à compléter/aligner avec PgBouncer et Alloy.

### Violations déjà observées

- `.gitlab-ci.yml` inclut `infrastructure/ci-templates` au lieu de `croo-dev/ci-cd-unified-template-v1.0`.
- Pipeline contient des stages `migrate-*`, interdits par § 4.2 et § 4.12.
- `deploy/helm/` et `deploy/scripts/` portent de la logique qui doit vivre dans le repo CI/CD partagé (§ 4.1, § 8.3).
- `deploy/helm/api-chart/templates/deployment.yaml` ne contient pas l'initContainer `migrate` avec `scripts/migrate_with_lease.py`.
- `deploy/helm/api-chart` ne contient pas le RBAC Lease Kubernetes requis.
- `deploy/helm/gateway-chart/templates/ingress.yaml` route encore `apiRoutes.apis`; le gateway doit exposer les B4F seulement.
- Plusieurs backends appellent `Base.metadata.create_all(...)` au démarrage, interdit par § 2.7.5.
- Certaines B4F appellent des services externes directement, notamment MS365/Membrane; la règle v1.4 exige de déplacer ces intégrations côté Backend.
- Le frontend repose surtout sur `shared/services/*.service.ts`; le store NGRX par B4F reste à structurer.
- Un dossier d'outil local `.kilo/` existait à la racine et doit être supprimé selon § 10.3.

## Phase 0 - Skills et source de vérité

But: rendre le dépôt autonome et aligné avec § 10.3 et § 10.4.

- Versionner `docs/regles-architecture-deploiement.md`.
- Installer `.agents/skills/` depuis `croo-dev/code-agent-skills-v1.0`.
- Ajouter `.agents/update-skills.sh` et `.agents/.skills-version`.
- Valider les skills avec `scripts/validate-skills.sh` du repo central.
- Garder `AGENTS.md` court: source de vérité, cible de refactor, validation.
- Supprimer les dossiers/fichiers d'outils spécifiques interdits par § 10.3.

Skills utiles: `dx_base_create_install_skills_in_project`, `dx_base_check_agents_dir_present`, `dx_base_check_update_skills_script_present`, `dx_base_check_no_tool_specific_dirs`, `dx_intermediate_check_project_conventions`.

## Phase 1 - Architecture API deux tiers (§ 2, § 8.1)

But: garantir que B4F, Backends, DB et event bus respectent la séparation stricte.

- Auditer tous les dossiers `apis/exposed/` et `apis/internal/`.
- Confirmer qu'aucune B4F ne possède `alembic/`, modèles DB ou `DATABASE_URL`.
- Confirmer qu'aucune route frontend ou gateway ne cible un Backend.
- Identifier les B4F proxy CRUD 1:1 et décider: enrichir logique B4F ou fusionner/réorganiser.
- Déplacer les appels services externes depuis les B4F vers des Backends.
- Remplacer tout HTTP Backend->Backend par événements Redis.
- Standardiser `apis/exposed/shared/` et `apis/internal/shared/`, sans logique métier.

Skills utiles: `dx_intermediate_analyse_apis`, `dx_intermediate_check_apis`, `dx_base_check_api_no_db_in_b4f`, `dx_base_check_api_no_backend_in_ingress`, `dx_base_check_api_no_frontend_to_backend`, `dx_base_check_api_no_http_between_backends`, `dx_base_create_split_responsibilities_b4f_backend`.

## Phase 2 - Alembic et DB (§ 2.7, § 8.1)

But: supprimer toute DDL runtime et rendre les migrations réversibles.

- Supprimer tous les `Base.metadata.create_all(...)`.
- Vérifier que la première migration de chaque Backend crée le schéma, les tables, droits et privilèges.
- Vérifier que chaque migration a un `downgrade()` non vide et symétrique.
- Convertir tout `.sql` manuel en migration Alembic.
- Ajouter les tests `alembic downgrade -1 && alembic upgrade head`.
- Confirmer PgBouncer transaction mode, pools bas et prepared statements désactivés.

Skills utiles: `dx_base_check_alembic_no_create_all_in_code`, `dx_base_check_alembic_all_ddl_in_alembic`, `dx_base_check_alembic_first_revision_creates_schema`, `dx_base_check_alembic_downgrade_not_empty`, `dx_base_check_alembic_downgrade_symmetric`, `dx_base_create_alembic_run_tests_with_downgrade`.

## Phase 3 - CI/CD v1.4 (§ 4, § 8.3)

But: remplacer la CI projet par le modèle parent/child du repo partagé.

- Réduire `.gitlab-ci.yml` aux deux includes du repo `croo-dev/ci-cd-unified-template-v1.0`, taggés sur la même version.
- Supprimer les stages `migrate-*`; les migrations vivent dans l'initContainer.
- Supprimer `allow_failure: true`.
- Exiger couverture 85 %, JUnit, Cobertura, `coverage:` regex et `artifacts: when: always`.
- Vérifier Kaniko, Harbor, `verify:<api>`, signature Cosign et absence de tag `latest`.
- Vérifier les triggers: `main` vers dev auto, MR vers review auto, tag `v*` vers staging/prod manuel.

Skills utiles: `dx_intermediate_create_cicd_pipeline`, `dx_intermediate_check_cicd_pipeline`, `dx_base_check_cicd_canonical_includes`, `dx_base_check_cicd_no_migration_stage`, `dx_base_check_cicd_no_allow_failure`, `dx_base_check_cicd_verify_job`.

## Phase 4 - Kubernetes, gateway et charts (§ 5, § 8.4)

But: un seul point d'entrée, backends internes, migrations par Lease Kubernetes.

- Migrer `deploy/helm/` et `deploy/scripts/` vers le modèle values-only attendu par le repo partagé.
- Ajouter ou consommer l'initContainer `migrate` des Backends.
- Ajouter le RBAC Lease `coordination.k8s.io`.
- Retirer tout Backend du gateway.
- S'assurer que le gateway route `/` vers le frontend et `/api/<service>/v1` vers les B4F seulement.
- Vérifier HTTPS redirect, wildcard TLS, copie depuis `cert-manager`, namespaces canoniques et kubeconfig par indirection.

Skills utiles: `dx_intermediate_check_k8s_config`, `dx_base_check_api_migration_initcontainer`, `dx_base_check_api_migration_lease`, `dx_base_check_gateway_routes_frontend_root`, `dx_base_check_gateway_routes_apis_under_api_prefix`, `dx_base_check_gateway_uses_wildcard_tls`.

## Phase 5 - Harbor et registry (§ 7, § 8.6)

But: Harbor devient la registry primaire, avec robot accounts, scan et signature.

- Vérifier `HARBOR_URL`, `HARBOR_PROJECT`, `HARBOR_ROBOT_USER`, `HARBOR_ROBOT_TOKEN`.
- Retirer toute dépendance à `CI_REGISTRY_*` et `DEPLOY_TOKEN_*`.
- Vérifier `imagePullSecrets`, ServiceAccount et provisionnement par environnement.
- Confirmer auto-scan, auto-sign Cosign, retention et allow-list CVE côté repo partagé.

Skills utiles: `dx_intermediate_check_registry_to_k8s`, `dx_base_check_registry_harbor_primary`, `dx_base_check_registry_robot_account`, `dx_base_check_registry_imagepullsecrets`, `dx_base_check_cicd_kaniko_image_harbor`.

## Phase 6 - Frontend Angular/NGRX (§ 3, § 14, § 8.2, § 8.12)

But: aligner le frontend avec un service et un feature store par B4F.

- Cartographier B4F -> service Angular -> feature NGRX.
- Déplacer les appels HTTP vers Effects + Services.
- Éliminer les services injectés directement dans les components pour chargement d'état.
- Mapper les DTO HTTP vers modèles domaine avant stockage NGRX.
- Ajouter Playwright E2E dans `frontend/e2e/`, hors pipeline CI.
- Ajouter un hook pre-commit smoke E2E pour changements frontend.

Skills utiles: `dx_intermediate_analyse_frontend_ngrx`, `dx_intermediate_check_frontend_ngrx`, `dx_intermediate_check_frontend_clean_archi`, `dx_base_create_frontend_feature_full`, `dx_base_create_frontend_e2e_test_skeleton`, `dx_base_create_frontend_husky_pre_commit`.

## Phase 7 - Observabilité et probes (§ 5.8 à § 5.10, § 8.8)

But: rendre les APIs observables et smoke-testables.

- Vérifier `/liveness`, `/readiness`, `/startup`, `/health`, `/metrics` sur chaque API.
- S'assurer que `/liveness` n'appelle aucun service externe.
- S'assurer que `/health` liste toutes les dépendances avec statut et latence.
- Propager `traceparent` et `trace_id` sur HTTP, logs et événements Redis.
- Configurer OTel vers Alloy, sampling dev/prod et logs JSON stdout/stderr.

Skills utiles: `dx_intermediate_check_k8s_config`, `dx_base_check_k8s_health_endpoints`, `dx_base_check_k8s_metrics_endpoint`, `dx_base_check_k8s_traceparent_propagation`, `dx_base_check_k8s_trace_id_in_events`, `dx_base_check_k8s_logs_stdout_json`.

## Phase 8 - Développement local et conventions (§ 10, § 11, § 12)

But: rendre un checkout local reproductible et uniforme.

- Ajouter/aligner `run_all_apis.sh`, `migrate_all_apis.sh`, `run_all_apis_tests.sh`, `run_frontend.sh`, `run_frontend_tests.sh`, `run_frontend_e2e.sh`.
- Vérifier `run_api.sh`, `run_tests.sh`, et `migrate.sh` uniquement dans les Backends.
- Aligner `docker-compose.yml` avec `postgres`, `pgbouncer`, `redis`, `alloy`.
- Ajouter `.env.example`, sans secret de production.
- Appliquer la structure Clean Architecture: `domain/`, `application/`, `infrastructure/`, `presentation/`.
- Ajouter import-linter ou équivalent pour bloquer les dépendances interdites.

Skills utiles: `dx_intermediate_check_local_dev`, `dx_intermediate_create_local_dev`, `dx_intermediate_check_clean_archi_apis`, `dx_base_check_local_dev_root_wrappers`, `dx_base_check_local_dev_docker_compose`, `dx_base_create_enforce_uniform_api_structure`.

## Phase 9 - Validation finale et rapport (§ 8, § 9)

But: prouver la conformité après refactor.

- Exécuter `dx_master_check` comme guide de revue complète.
- Remplir `Cameleon/matrice-validation-conformite-v1.4.md`.
- Produire le rapport au format § 9.
- Joindre les preuves: commandes, fichiers, captures UI si frontend touché, pipeline ou smoke-test si disponible.
- Classer chaque écart restant: `critique`, `à corriger`, `non applicable`, `bloqué`.

## Ordre recommandé des MRs

1. Règles, skills, matrice et hygiène du dépôt.
2. CI/CD v1.4 minimale et values-only.
3. Helm/initContainer/Lease via template partagé.
4. Suppression DDL runtime et durcissement Alembic.
5. Gateway: frontend + B4F seulement.
6. Déplacement services externes hors B4F.
7. Event bus Redis entre Backends.
8. Frontend NGRX par B4F.
9. Probes, observabilité, local dev et rapport final.

## Définition de terminé

- `docs/regles-architecture-deploiement.md` est versionné et appliqué.
- `.agents/skills/` contient les skills `dx_*` officiels et validés.
- `.agents/update-skills.sh` et `.agents/.skills-version` sont présents.
- Aucun ancien workflow local ou dossier d'outil spécifique interdit ne reste actif.
- La matrice de conformité est remplie avec preuves.
- Le rapport final suit le format § 9.
- Chaque violation critique est corrigée ou explicitement bloquée avec cause vérifiable.
