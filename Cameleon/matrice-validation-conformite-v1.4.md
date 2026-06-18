# Matrice de validation de conformité v1.4

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Source de vérité: `docs/regles-architecture-deploiement.md`
Skills de conversion: `Cameleon/skills/`
Skills officiels de référence: `.agents/skills/`, version `v1.7.0`

## Légende

| Statut | Sens |
|---|---|
| OK | Conforme avec preuve vérifiée |
| VIOLATION | Non conforme, correction requise |
| A_VERIFIER | Pas assez de preuve |
| N/A | Non applicable à CDE |
| BLOQUE | Validation impossible sans accès externe ou décision |
| SKIP_CI_CD | CI/CD, Harbor ou registry volontairement hors périmètre actif |

Criticité: `critique` si la règle bloque sécurité, déploiement, rollback ou isolation; `à corriger` sinon.

## Matrice maître

| ID | Section | Domaine | Skill de validation | Preuve attendue | Statut initial | Criticité |
|---|---:|---|---|---|---|---|
| M-00 | § 10.3-10.4 | Source de vérité et skills | `cde-check-local-dev` | `AGENTS.md`, `.agents/skills/`, `.agents/update-skills.sh`, `.agents/.skills-version`, `Cameleon/skills/` | OK | critique |
| M-01 | § 2, § 8.1 | Architecture APIs deux tiers | `cde-check-api-boundaries` | Arborescence `apis/exposed`, `apis/internal`, absence DB dans B4F, absence backend dans gateway | OK | critique |
| M-02 | § 2.7 | Alembic et DB | `cde-check-database-alembic` | Aucune DDL runtime, migrations avec schema + downgrade local testé | OK | critique |
| M-03 | § 3, § 14 | Frontend Angular/NGRX | `cde-check-frontend-ngrx` | Store feature par B4F, HTTP dans Effects, modèles domaine | VIOLATION | à corriger |
| M-04 | § 4, § 8.3 | CI/CD | `cde-master-validation` | Hors périmètre actif: CI/CD non suivi faute d'éléments plateforme | SKIP_CI_CD | critique |
| M-05 | § 5, § 8.4 | Kubernetes et gateway | `cde-check-k8s-gateway` | Gateway unique, Backends internes, initContainer migrate, Lease RBAC | OK | critique |
| M-06 | § 6, § 8.5 | Variables d'environnement | `cde-check-local-dev` | Variables locales documentées, pas de secrets réels, `.env.example` | OK | critique |
| M-07 | § 7, § 8.6 | Harbor registry | `cde-master-validation` | Hors périmètre actif: Harbor/registry dépend des éléments CI/CD manquants | SKIP_CI_CD | critique |
| M-08 | § 5.8-5.10, § 8.8 | Observabilité et probes | `cde-check-observability` | `/liveness`, `/readiness`, `/startup`, `/health`, `/metrics`, logs JSON, trace_id | OK | critique |
| M-09 | § 10, § 11 | Conventions et dev local | `cde-check-local-dev` | Wrappers racine, scripts par API, compose postgres/pgbouncer/redis/alloy | OK | à corriger |
| M-10 | § 12 | Clean Architecture API | `cde-check-clean-architecture` | `domain/application/infrastructure/presentation`, import-linter, tests par couche | VIOLATION | à corriger |
| M-11 | § 9 | Rapport final | `cde-master-validation` | Rapport markdown final, branches fusionnées, Docker local, CI/CD marqué skip | OK | critique |

## Matrice détaillée

### 1. Source de vérité et outillage portable

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| S-01 | `docs/regles-architecture-deploiement.md` est versionné | § 1, § 10.1 | `cde-check-local-dev` | Vérifier le fichier et les références dans `AGENTS.md` | OK | `docs/regles-architecture-deploiement.md` présent |
| S-02 | `AGENTS.md` existe à la racine | § 10.3 | `cde-check-local-dev` | `[ -f AGENTS.md ]` | OK | `AGENTS.md` présent |
| S-03 | `.agents/skills/` est présent et versionné | § 10.3-10.4 | `cde-check-local-dev` | `[ -d .agents/skills ]` + `find .agents/skills -name SKILL.md` | OK | 204 skills validées |
| S-04 | `update-skills.sh` présent | § 10.4 | `cde-check-local-dev` | `[ -x .agents/update-skills.sh ]` | OK | `.agents/update-skills.sh` présent |
| S-05 | Version des skills traçable | § 10.4 | `cde-check-local-dev` | Lire `.agents/.skills-version` | OK | `v1.7.0` |
| S-06 | Aucun dossier/fichier outil spécifique interdit | § 10.3 | `cde-check-local-dev` | `find` des patterns interdits | OK | `.kilo/` supprimé |
| S-07 | Aucun `SKILL.md` officiel modifié manuellement | § 10.4 | `cde-check-local-dev` | Comparer au repo central/tag | OK | `validate-skills.sh .agents/skills`: 204 skills validées, 0 échec; comparaison avec le tag central `v1.7.0` sans écart |
| S-08 | Skills Cameleon créés depuis les règles | § 9, § 10.4 | `cde-master-validation` | `find Cameleon/skills -name SKILL.md` + `quick_validate.py` | OK | 8 skills locaux validés: API boundaries, DB/Alembic, K8s/gateway, frontend NGRX, observabilité, dev local, Clean Architecture, validation finale |

### 2. Architecture APIs

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| A-01 | B4F sous `apis/exposed/`, Backends sous `apis/internal/` | § 2.1 | `cde-check-api-boundaries` | `find apis/exposed apis/internal` | OK | Structure présente |
| A-02 | Aucune B4F avec DB/Alembic/`DATABASE_URL` | § 2.2 | `cde-check-api-boundaries` | Recherche `alembic`, `DATABASE_URL`, SQLAlchemy dans `apis/exposed` | OK | `find apis/exposed -type d \( -name alembic -o -name versions \) -print` ne retourne rien; `rg "DATABASE_URL|SQLAlchemy|sqlalchemy|create_engine|sessionmaker|declarative_base|metadata\.create_all|db\.create_all|SQLModel\.metadata" apis/exposed -g '*.py' -g '!**/tests/**'` ne retourne rien |
| A-03 | Aucun Backend dans le gateway | § 2.3, § 5.11 | `cde-check-api-boundaries` | Lire gateway values/templates | OK | `find deploy -maxdepth 2 \( -name helm -o -name scripts \) -print` ne retourne rien; `deploy/values/*/gateway.yaml` contient seulement `routes.frontend`, `routes.apis: []`; les routes API sont découvertes par le template partagé depuis `apis/exposed/*-b4f-api` |
| A-04 | Frontend ne cible que les B4F | § 2.9 | `cde-check-api-boundaries` | Recherche `backend-api` dans `frontend/` | OK | `rg "backend-api|apis/internal|http://.*backend|https://.*backend|localhost:80(0[7-9]|1[0-9])" frontend/src -g '*.ts' -g '*.html' -g '*.json' -g '*.js'` ne retourne rien |
| A-05 | Aucun HTTP Backend->Backend | § 2.4 | `cde-check-api-boundaries` | Recherche clients HTTP dans `apis/internal` | OK | `email-backend-api` n'appelle plus `user-backend-api`; admin signé via JWT `role`/`is_super_admin`; `rg "create_service_client\(|httpx|requests|aiohttp|user~backend-api|/api/v1/users" apis/internal -g '*.py' -g '!**/tests/**'` ne retourne plus qu'une déclaration de route dans `user-backend-api` |
| A-06 | B4F porte logique métier, pas proxy CRUD 1:1 | § 2.2, § 2.8 | `cde-check-api-boundaries` | Lire routes B4F et clients backend | OK | Audit `Cameleon/audit-api-boundaries-v1.4.md`: `auth-b4f-api` porte JWT/session/rate-limit, `crm-b4f-api` `/dashboard/summary` compose le dashboard et agrege les statuts ouverts valides (9 passed), `kb-b4f-api` `/kb/home` (9 passed), `communication-b4f-api` `/integrations/overview` (7 passed), `ai-agent-b4f-api` chat/analyse comportementale, `platform-b4f-api` `/overview` et override workflow (9 passed) |
| A-07 | Backend possède une entité principale atomique | § 2.3 | `cde-check-api-boundaries` | Cartographier modèles par backend | OK | Audit `Cameleon/audit-api-boundaries-v1.4.md`: les 11 backends ont une entité principale/famille fonctionnelle et des secondaires liées; aucun dossier `domain/entities` ne montre une dépendance directe vers une autre famille backend |
| A-08 | Services externes seulement côté Backend | § 2.2-2.3 | `cde-check-api-boundaries` | Recherche clients MS365/Membrane dans B4F | OK | Routes provider B4F remplacées par proxys minces vers `email-backend-api` `/api/v1/provider/{ms365,membrane}`; scan B4F sans hit code pour `httpx`, `graph.microsoft`, `MembraneClient`, `MS365GraphService`, `generate_membrane_token`, `workspace_secret`, `client_secret`; clients externes sous `apis/internal/email-backend-api/app/infrastructure/external`; tests locaux ciblés OK: `communication-b4f-api` 6 passed, `email-backend-api` 11 passed |
| A-09 | Redis event bus présent | § 2.4 | `cde-check-api-boundaries` | Vérifier `REDIS_URL`, compose, Helm, publishers/subscribers | OK | `docker-compose.yml` définit `REDIS_URL` et `EVENT_BUS_BACKEND=redis`; les 33 values backend dev/staging/prod déclarent `externalDependencies: redis`; les 11 backends importent `shared.event_bus` au démarrage et possèdent `app/events/publishers.py` |

### 3. Alembic et base de données

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| DB-01 | Aucune DDL au startup | § 2.7.5 | `cde-check-database-alembic` | `rg "create_all|db.create_all|DDL"` | OK | `rg "metadata\\.create_all|db\\.create_all|SQLModel\\.metadata\\.create_all|drop_all\\(" apis -g '*.py'` ne retourne aucune DDL runtime |
| DB-02 | Toute DDL passe par Alembic | § 2.7.5 | `cde-check-database-alembic` | Chercher `.sql`, `CREATE TABLE`, `CREATE SCHEMA` hors versions | OK | `rg "CREATE TABLE|CREATE SCHEMA|ALTER TABLE|DROP TABLE|DROP SCHEMA|GRANT |ALTER DEFAULT PRIVILEGES|op\.execute|create_all|drop_all" apis/internal -g '*.py' -g '!**/alembic/versions/**' -g '!**/tests/**'` ne retourne rien; les `CREATE SCHEMA` ont été retirés des `env.py` |
| DB-03 | Première migration crée le schéma du service | § 2.7.2, § 2.7.5 | `cde-check-database-alembic` | Lire première révision par backend | OK | 11 migrations initiales contiennent `CREATE SCHEMA IF NOT EXISTS`, `GRANT USAGE, CREATE`, `GRANT ALL ON ALL TABLES`, `GRANT ALL ON ALL SEQUENCES` et `ALTER DEFAULT PRIVILEGES`, pilotés par `DB_USERNAME`; les tables de version Alembic sont nommées par service dans `public` (`<service>_alembic_version`) pour permettre base vide + `downgrade base` sans DDL hors migration |
| DB-04 | Downgrade non vide | § 2.7.5 | `cde-check-database-alembic` | `rg "def downgrade|pass|NotImplementedError"` | OK | 14 migrations sur 14 contiennent `def downgrade() -> None`; `rg "\bpass\b|NotImplementedError|op\.create_table\('alembic_version'" apis/internal/*-backend-api/alembic/versions/*.py` ne retourne rien |
| DB-05 | Downgrade symétrique | § 2.7.5 | `cde-check-database-alembic` | Comparer opérations upgrade/downgrade | OK | Compteurs statiques alignés: `op.create_table` 70 / `op.drop_table` 70, `op.create_index` 181 / `op.drop_index` 181, `op.add_column` 1 / `op.drop_column` 1, `CREATE SCHEMA` 11 / `DROP SCHEMA` 11; PostgreSQL jetable validé sur `email-backend-api` et `activity-backend-api`: `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head` |
| DB-06 | CI teste downgrade puis upgrade | § 2.7.5, § 4.9 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Preuve locale manuelle OK sur `email-backend-api` et `activity-backend-api`; validation CI volontairement ignorée tant que le volet CI/CD est exclu |
| DB-07 | InitContainer exécute `scripts/migrate_with_lease.py` | § 2.7.5 | `cde-check-k8s-gateway` | Lire deployment chart/values | OK | `deploy/values/*/*-backend-api.yaml` active `initContainers.migrate.enabled`; chart partagé `api-chart` lance `/app/scripts/migrate_with_lease.py` |
| DB-08 | Lease Kubernetes et RBAC présents | § 2.7.5 | `cde-check-k8s-gateway` | Chercher `coordination.k8s.io`, `leases` | OK | Chart partagé `api-chart/templates/migration-lease-rbac.yaml` fournit Lease/RBAC; les backends activent l'initContainer |
| DB-09 | Pool SQLAlchemy compatible PgBouncer | § 2.7.3-2.7.4 | `cde-check-database-alembic` | Lire `apis/shared/database` | OK | `apis/shared/database/connection.py` borne `DB_POOL_SIZE` et `DB_MAX_OVERFLOW` à 5, garde `pool_pre_ping=True`, `pool_recycle=300`, ajoute `connect_args={"prepare_threshold": None}` pour `postgresql+psycopg`, et applique `SET LOCAL search_path` par API au début des transactions pour PgBouncer transaction mode; contrôle Python dans `activity-backend-api` OK |

### 4. CI/CD

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| CI-01 | `.gitlab-ci.yml` inclut seulement le repo partagé v1.0 | § 4.1 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | CI/CD non suivi à la demande du user; conserver les constats existants sans nouvelle action |
| CI-02 | Includes taggés, jamais `main` | § 4.1, § 4.12 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | CI/CD non suivi à la demande du user; conserver les constats existants sans nouvelle action |
| CI-03 | Parent/child et 5 stages seulement | § 4.2 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | CI/CD non suivi à la demande du user; ne pas traiter l'écart upstream dans cette conversion |
| CI-04 | Aucun stage de migration | § 4.2, § 4.12 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | CI/CD non suivi à la demande du user; migrations validées côté initContainer/local |
| CI-05 | Aucun `allow_failure: true` | § 4.9 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | CI/CD non suivi à la demande du user |
| CI-06 | Couverture 85 %, JUnit, Cobertura | § 4.9 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Tests locaux par lot conservés comme preuve; couverture pipeline exclue |
| CI-07 | Kaniko + Harbor, pas Docker-in-Docker | § 4.10 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Harbor/build pipeline exclus faute d'éléments plateforme |
| CI-08 | Job `verify:<api>` Harbor/Cosign | § 4.10 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Harbor/Cosign exclus faute d'éléments plateforme |
| CI-09 | Pas de déploiement auto staging/prod | § 4.3 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | CI/CD non suivi à la demande du user |
| CI-10 | Projet values-only, pas de scripts/charts partagés locaux | § 4.1, § 8.3 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Les constats repo-local restent dans K8s/local-dev; suivi CI/CD exclu |

### 5. Kubernetes et gateway

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| K-01 | Envs canoniques `dev/staging/prod` | § 5.1 | `cde-check-k8s-gateway` | Lire deploy values | OK | Dossiers values dev/staging/prod |
| K-02 | `NAMESPACE` non hardcodé | § 5.3 | `cde-check-k8s-gateway` | Lire values/scripts repo-local | OK | Aucun namespace hardcodé dans les values projet; la résolution CI/CD reste hors périmètre actif |
| K-03 | `KUBECONFIG_VARIABLE`, pas variable directe | § 5.4 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Dépend du template CI/CD et des variables plateforme; non suivi dans cette passe |
| K-04 | Gateway unique par namespace | § 5.11 | `cde-check-k8s-gateway` | Lire charts/values | OK | Gateway porté par le modèle partagé; le repo CDE conserve des values gateway |
| K-05 | Gateway route `/` vers frontend | § 5.11-5.12 | `cde-check-k8s-gateway` | Lire values gateway | OK | `frontendRoute` présent |
| K-06 | Gateway route `/api/<service>/v1` vers B4F seulement | § 5.11 | `cde-check-k8s-gateway` | Lire routes/values et APIs exposées | OK | Les routes publiques sont alignées côté frontend/B4F; aucun Backend n'est listé comme route publique projet |
| K-07 | HTTPS redirect et wildcard TLS | § 5.7, § 5.11 | `cde-check-k8s-gateway` | Lire values/annotations | OK | `deploy/values/{dev,staging,prod}/gateway.yaml` définit `tls.secretName: wildcard-tls`, `tls.sourceNamespace: cert-manager`, `nginx.ingress.kubernetes.io/ssl-redirect: 'true'` et `force-ssl-redirect: 'true'` |
| K-08 | Probes health non authentifiées | § 5.10 | `cde-check-observability` | Appeler/lire routes API | OK | `auth_middleware.py` bypass `/health`, `/readiness`, `/liveness`, `/startup`, `/metrics`; test direct FastAPI retourne 200 pour les cinq endpoints |

### 6. Registry Harbor

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| R-01 | Harbor registry primaire | § 7.1 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Harbor/registry exclus faute d'éléments plateforme |
| R-02 | Robot account Harbor | § 7.2-7.3 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Robot account et variables GitLab exclus faute d'éléments plateforme |
| R-03 | Aucun `CI_REGISTRY_*` / `DEPLOY_TOKEN_*` | § 7.3, § 8.6 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Registry exclue; ne pas poursuivre les validations CI/CD/Harbor dans cette passe |
| R-04 | `imagePullSecrets` et ServiceAccount | § 7.7 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Dépend du provisioning environnement; non vérifiable repo-localement |
| R-05 | Verify Harbor + Cosign | § 4.10, § 7.7 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Harbor/Cosign exclus faute d'éléments plateforme |

### 7. Frontend

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| F-01 | Un service Angular par B4F | § 3.1 | `cde-check-frontend-ngrx` | Mapper services vers B4F | OK | Audit `Cameleon/audit-frontend-ngrx-v1.4.md`: services B4F ajoutés pour les compositions CRM, KB, Communication et Platform; services legacy par entité conservés comme support |
| F-02 | Un feature NGRX par B4F | § 3.1 | `cde-check-frontend-ngrx` | Chercher `store/<feature>` | OK | `frontend/src/app/store/{auth,crm,communication,ai-agent,platform,kb}` + `provideStore/provideEffects`; Docker frontend compile et sert `http://localhost:4700` après renouvellement du volume `node_modules` |
| F-03 | Aucun HTTP hors Effects | § 3.1-3.6 | `cde-check-frontend-ngrx` | Recherche `HttpClient`/services dans components | VIOLATION | Le dashboard et les lectures de listes `organizations`, `contacts`, `opportunities`, `activities` sont migres vers `CrmEffects` -> `CrmB4fService`; endpoints Docker B4F CRM en `HTTP 200`; creation/search/enrich et pages legacy restent hors Effects |
| F-04 | Templates utilisent `| async` | § 3.1 | `cde-check-frontend-ngrx` | Lire templates critiques | VIOLATION | `frontend/src/app/pages/dashboard/dashboard.html` lit `vm$ | async`; listes CRM lisent le store via signals et captures locales sans banniere `Request failed`; migration `| async` incomplete ailleurs, voir `Cameleon/audit-frontend-ngrx-v1.4.md` |
| F-05 | API base URL = `/api` | § 5.12 | `cde-check-frontend-ngrx` | Lire environments | OK | Production utilise `/api/<b4f>/v1` et le frontend chart injecte `API_BASE_URL=/api` |
| F-06 | Playwright E2E sous `frontend/e2e/` | § 3.8 | `cde-check-frontend-ngrx` | `find frontend/e2e` | OK | `frontend/e2e/smoke.spec.ts`, `frontend/playwright.config.ts`; `./run_frontend_e2e.sh --project=chromium` OK, 1 passed |
| F-07 | E2E absent du pipeline CI | § 3.8 | `cde-master-validation` | Hors périmètre actif | SKIP_CI_CD | Validation pipeline exclue; E2E à garder local-only dans cette passe |
| F-08 | Hook pre-commit smoke E2E | § 3.8 | `cde-check-frontend-ngrx` | Lire package/husky/scripts | OK | `frontend/.husky/pre-commit` lance `npm run e2e -- --project=chromium`; wrapper racine `run_frontend_e2e.sh` validé |

### 8. Observabilité

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| O-01 | Logs JSON stdout/stderr | § 5.8 | `cde-check-observability` | Lire logging shared | OK | `shared.infrastructure.logging.configure_logging` utilise `structlog.processors.JSONRenderer()` par défaut, écrit sur `sys.stdout`, merge les contextvars et les APIs appellent `configure_logging(settings.log_level, settings.log_format)` |
| O-02 | `/metrics` sur chaque API | § 5.8, § 5.10 | `cde-check-observability` | Lire routes / appeler local | OK | Toutes les APIs incluent `monitoring_router`; test direct FastAPI confirme `/metrics` en Prometheus text format |
| O-03 | OTel vers Alloy | § 5.8 | `cde-check-observability` | Lire env/compose/chart | OK | `docker compose --env-file .env.example config` expose `alloy`, `OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4317`; l'image `grafana/alloy:v1.5.1` démarre avec `observability/alloy/config.alloy` |
| O-04 | Propagation `traceparent` | § 5.9 | `cde-check-observability` | Lire HTTP client/middleware | OK | `RequestLoggingMiddleware` extrait ou génère `traceparent`, lie `trace_id/request_id` aux logs, renvoie les headers; `shared.services.HTTPClient` propage `traceparent` et `x-request-id`; test `activity-backend-api` OK |
| O-05 | `trace_id` dans events Redis | § 2.4, § 5.9 | `cde-check-observability` | Lire schemas event bus | OK | `shared.event_bus.Event` porte `trace_id`, le sérialise dans `to_dict()`/`from_dict()`, et le remplit depuis le contexte courant; test publisher `activity-backend-api` OK |
| O-06 | `/health` liste dépendances | § 5.10 | `cde-check-observability` | Lire routes / appeler local | OK | `monitoring.py` retourne `dependencies` avec `database`, `redis`, `otel`; test direct FastAPI confirme le champ dans `/health` |

### 9. Développement local et conventions

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| L-01 | Wrappers racine présents | § 11.1 | `cde-check-local-dev` | `ls run_* migrate_all_apis.sh` | OK | Wrappers exécutables: `run_all_apis.sh`, `migrate_all_apis.sh`, `run_all_apis_tests.sh`, `run_all_tests.sh`, `run_frontend.sh`, `run_frontend_tests.sh`, `run_frontend_e2e.sh` |
| L-02 | Scripts par API uniformes | § 11.2 | `cde-check-local-dev` | `find apis -name run_api.sh -o -name run_tests.sh` | OK | 17 APIs ont `run_api.sh` + `run_tests.sh`; 11 Backends ont `migrate.sh`; B4F `run_tests.sh` produit `junit.xml` + `coverage.xml` avec seuil 85 % |
| L-03 | B4F sans `migrate.sh` | § 11.2 | `cde-check-local-dev` | `find apis/exposed -name migrate.sh` | OK | `find apis/exposed -name migrate.sh` retourne 0 fichier |
| L-04 | Compose postgres + pgbouncer + redis + alloy | § 11.3 | `cde-check-local-dev` | Lire `docker-compose.yml` | OK | `docker compose --env-file .env.example config --quiet` passe; services `database`, `pgbouncer`, `redis`, `alloy` présents; PgBouncer en `transaction`; `docker compose --env-file .env.example up -d --build` terminé avec 11 Backends healthy, 6 B4F healthy et frontend `http://localhost:4700` en `HTTP/1.1 200 OK` |
| L-05 | `.env.example` à jour | § 11.4 | `cde-check-local-dev` | `[ -f .env.example ]` + variables | OK | Variables globales `DB_HOST`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`, `DATABASE_SSLMODE`, `REDIS_URL`, `OTEL_EXPORTER_OTLP_ENDPOINT`; ports préfixés par API |
| L-06 | Docs sous `/docs` | § 10.1 | `cde-check-local-dev` | Chercher docs hors racine autorisée | OK | `Cameleon/` est le dossier de plan de conversion demandé; hors `docs/`/`Cameleon/`, seuls `AGENTS.md`, `README.md`, `frontend/README.md` et `apis/shared/requirements.txt` existent comme conventions racine/manifests techniques |
| L-07 | Pas de données client réelles | § 10.2 | `cde-check-local-dev` | Scan secrets/data | OK | Audit `Cameleon/audit-local-dev-clean-architecture-v1.4.md`: `.env` ignoré, `.env.example` versionné, scan Git sans clé privée/token évident, values Kubernetes via `secretRefs`; fallback Docker local explicitement `dev-only-secret-not-for-production` |

### 10. Clean Architecture

| ID | Règle | Section | Skill | Méthode de validation | Statut initial | Preuve actuelle / à collecter |
|---|---|---:|---|---|---|---|
| CA-01 | APIs en 4 couches uniformes | § 12.2 | `cde-check-clean-architecture` | `find apis -maxdepth` + import graph | OK | Les 17 APIs ont `domain/application/infrastructure/presentation`; les couches ajoutees sont des packages vides pour garde-fous avant extraction verticale |
| CA-02 | `domain/` sans framework | § 12.3 | `cde-check-clean-architecture` | Recherche imports FastAPI/SQLAlchemy/Pydantic dans domain | OK | Les modèles ORM ont été déplacés vers `app/infrastructure/persistence/models`; scan `app/domain` pour SQLAlchemy, FastAPI, Pydantic, `Column` et `relationship`: aucun résultat |
| CA-03 | `application/` sans framework | § 12.3 | `cde-check-clean-architecture` | Recherche imports FastAPI/SQLAlchemy/Pydantic dans application | OK | Scan direct `apis/*/*/app/application` pour FastAPI, SQLAlchemy, httpx, redis, pydantic_settings et `app.presentation`: aucun résultat; helper Membrane tenant-key extrait hors route; `activity-backend-api`, `product-backend-api`, `contact-backend-api`, `org-backend-api`, `opportunity-backend-api`, `user-backend-api`, `usage-backend-api`, `kb-backend-api` et une partie de `agent-backend-api` ajoutent des use cases sans dépendance FastAPI/SQLAlchemy directe |
| CA-04 | Routes sans logique métier | § 12.3 | `cde-check-clean-architecture` | Lire routes longues/complexes | VIOLATION | `activity-backend-api`, `product-backend-api`, `contact-backend-api`, `org-backend-api`, `opportunity-backend-api`, `user-backend-api`, `usage-backend-api`, `kb-backend-api` et les routes Agent `capability`, `client_map`, `training` ont maintenant des routes minces qui appellent des use cases; la violation reste ouverte car plusieurs routes contiennent encore persistence/logique métier, exemples: `provider_membrane_routes.py`, `bcc_routes.py`, `bob_settings_routes.py`, `workflow_routes.py`, `auth_routes.py` |
| CA-05 | Entités métier ne dérivent pas de SQLAlchemy/Pydantic | § 12.3 | `cde-check-clean-architecture` | Recherche `Base`, `BaseModel` dans domain entities | OK | `app/domain/entities` ne porte plus les modèles ORM; les classes SQLAlchemy résident sous `app/infrastructure/persistence/models` |
| CA-06 | Import-linter configuré | § 12.3 | `cde-check-clean-architecture` | Lire config test/lint | OK | Les 17 `pyproject.toml` contiennent 3 contrats import-linter progressifs, dont `domain avoids framework dependencies`; `lint-imports --config pyproject.toml --no-cache` passe sur les 17 APIs, 51 contrats gardes, 0 brise |

## Commandes de validation recommandées

```bash
# Skills officiels
tmpdir=$(mktemp -d)
git clone --depth 1 --branch "$(cat .agents/.skills-version)" git@gitlab.tools.thesmartcrew.com:croo-dev/code-agent-skills-v1.0.git "$tmpdir/skills"
bash "$tmpdir/skills/scripts/validate-skills.sh" .agents/skills
rm -rf "$tmpdir"

# Skills Cameleon
for d in Cameleon/skills/*; do
  python3 /Users/alexandregauthier/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$d"
done

# Source/règles/outillage
test -f AGENTS.md
test -d .agents/skills
test -x .agents/update-skills.sh
find . -maxdepth 3 \( -name '.kilo*' -o -name '.cursor*' -o -name '.claude*' -o -name '.aider*' -o -name '.continue*' -o -name '.windsurf*' -o -name '.codeium*' -o -name '.copilot*' -o -name 'CLAUDE.md' \) -not -path './.git/*'

# Validations repo-locales hors CI/CD
rg "create_all|db.create_all|SQLModel.metadata.create_all" apis
find deploy -maxdepth 2 \( -name helm -o -name scripts \) -print
rg "APIRouter\\(prefix=\"/api/v1|@router\\.(get|post|put|delete|patch)\\(\"/api/v1" apis/exposed/*-b4f-api/app/presentation/routes
find apis -mindepth 2 -maxdepth 2 \( -name pyproject.toml -o -name setup.py \) -print

# Matrice / rapport
# Utiliser Cameleon/skills/cde-master-validation pour produire le rapport final au format § 9.
```

## Critères de sortie

- Tous les `VIOLATION` critiques passent à `OK` ou `BLOQUE` avec justification vérifiable.
- Aucun `A_VERIFIER` ne reste avant la MR finale.
- Le rapport § 9 est produit avec les fichiers/lignes de preuve.
- Les branches de conversion sont fusionnées ensemble.
- Docker local est monté et son résultat est documenté.
- Les captures UI sont présentes dans `captures/` quand le frontend est touché.
