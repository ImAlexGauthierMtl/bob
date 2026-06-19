# Matrice de certification des règles d'architecture CDE v1.5

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Source de vérité: `/Users/alexandregauthier/Downloads/regles-architecture-deploiement.md`
Périmètre actif: code, architecture locale, frontend, APIs, DB, observabilité, valeurs de déploiement projet.
Périmètre exclu: CI/CD, Harbor, registry, runners et variables GitLab, selon décision de skip CI/CD.

## Objectif

Cette matrice sert à certifier qu'un refactor respecte les règles d'architecture et de déploiement du projet. Elle doit être utilisée avant une MR finale ou avant de déclarer une conversion terminée.

Une certification est accordée seulement si:

- aucun critère `BLOQUANT` n'est en `VIOLATION`, `A_CERTIFIER` ou `BLOQUE`;
- tous les éléments `MAJEUR` sont `OK` ou portent une justification écrite;
- les preuves sont reproductibles localement ou attachées dans `Cameleon/`;
- les captures UI sont présentes dans `captures/` quand le frontend est modifié;
- les éléments CI/CD restent explicitement `SKIP_CI_CD` tant que le périmètre est exclu.

## Statuts

| Statut | Sens |
| --- | --- |
| `OK` | Conforme avec preuve reproductible |
| `VIOLATION` | Non conforme, bloque la certification si critique |
| `A_CERTIFIER` | Test défini mais pas encore exécuté |
| `BLOQUE` | Validation impossible sans accès ou décision externe |
| `N/A` | Non applicable au repo |
| `SKIP_CI_CD` | Hors périmètre actif par décision explicite |

## Niveaux

| Niveau | Effet |
| --- | --- |
| `BLOQUANT` | Empêche la certification |
| `MAJEUR` | Doit être corrigé ou justifié |
| `MINEUR` | N'empêche pas la certification, mais doit être suivi |

## Matrice maître

| ID | Domaine | Certification attendue | Niveau | Statut |
| --- | --- | --- | --- | --- |
| CERT-00 | Source de vérité | Règles présentes, versionnées ou référencées, et matrice à jour | BLOQUANT | A_CERTIFIER |
| CERT-01 | Structure APIs deux tiers | B4F sous `apis/exposed`, Backends sous `apis/internal`, responsabilités séparées | BLOQUANT | A_CERTIFIER |
| CERT-02 | Frontend vers B4F seulement | Aucun appel direct frontend vers Backend interne | BLOQUANT | A_CERTIFIER |
| CERT-03 | B4F sans DB ni externe direct | Aucune B4F ne possède Alembic, SQLAlchemy, `DATABASE_URL`, client externe direct | BLOQUANT | A_CERTIFIER |
| CERT-04 | Backend invisible hors cluster | Aucun Backend n'est exposé via gateway ou config frontend | BLOQUANT | A_CERTIFIER |
| CERT-05 | Backend sans HTTP vers Backend | Toute synchronisation inter-backend passe par event bus | BLOQUANT | A_CERTIFIER |
| CERT-06 | Alembic obligatoire | Toute DDL est en migration Alembic versionnée | BLOQUANT | A_CERTIFIER |
| CERT-07 | Downgrade Alembic | Chaque migration a un `downgrade()` non vide et symétrique | BLOQUANT | A_CERTIFIER |
| CERT-08 | PgBouncer compatible | Pools bornés, pre-ping, recycle, prepared statements désactivés | BLOQUANT | A_CERTIFIER |
| CERT-09 | Redis event bus | `REDIS_URL`, publishers/subscribers et payloads avec `trace_id` | MAJEUR | A_CERTIFIER |
| CERT-10 | Frontend Angular/NGRX | Services par B4F, features store, Effects pour appels HTTP, composants branchés au store | MAJEUR | A_CERTIFIER |
| CERT-11 | Routes et gateway | Gateway unique, frontend sur `/`, B4F sur `/api/<service>`, Backends internes | BLOQUANT | A_CERTIFIER |
| CERT-12 | Observabilité | Logs JSON, probes, `/metrics`, propagation `traceparent` | BLOQUANT | A_CERTIFIER |
| CERT-13 | Secrets et env | Aucun secret réel, `.env.example` complet, variables runtime centralisées | BLOQUANT | A_CERTIFIER |
| CERT-14 | Développement local | Wrappers racine, scripts API uniformes, Docker local opérationnel | MAJEUR | A_CERTIFIER |
| CERT-15 | Clean Architecture | `domain/application/infrastructure/presentation`, import-linter, pas de framework dans domain | MAJEUR | A_CERTIFIER |
| CERT-16 | UI et thème | Login, shell, pages et composants suivent le cahier UI CDE | MAJEUR | A_CERTIFIER |
| CERT-17 | Tests locaux | Tests ciblés, build frontend, E2E/smoke si frontend touché | MAJEUR | A_CERTIFIER |
| CERT-18 | CI/CD et Harbor | Pipeline partagé, Kaniko, verify Harbor/Cosign, smoke deploy | BLOQUANT | SKIP_CI_CD |

## Détail des critères

### CERT-00 — Source de vérité

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Règles disponibles | `test -f docs/regles-architecture-deploiement.md || test -f /Users/alexandregauthier/Downloads/regles-architecture-deploiement.md` | Fichier trouvé | A_CERTIFIER |
| `Cameleon/` contient les livrables de certification | `find Cameleon -maxdepth 1 -type f | sort` | Plan, matrices, audits, cahier UI | A_CERTIFIER |
| CI/CD marqué hors périmètre si non traité | Lire cette matrice | `SKIP_CI_CD` explicite | A_CERTIFIER |

### CERT-01 — Structure APIs deux tiers

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| B4F sous `apis/exposed` | `find apis/exposed -maxdepth 2 -type d -name '*-b4f-api'` | Tous les B4F listés | A_CERTIFIER |
| Backends sous `apis/internal` | `find apis/internal -maxdepth 2 -type d -name '*-backend-api'` | Tous les Backends listés | A_CERTIFIER |
| Aucun monolithe mixte | Revue routes + persistence par API | Pas d'API avec routes publiques + DB locale dans le même service | A_CERTIFIER |
| Authentication split | `rg "authentication" apis frontend deploy -g '!**/node_modules/**'` | Aucun terme runtime `authentication`; `auth` + `iam` seulement | A_CERTIFIER |

### CERT-02 — Frontend vers B4F seulement

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Aucun `backend-api` dans frontend | `rg "backend-api|apis/internal|localhost:80(0[7-9]|1[0-9])" frontend/src` | Aucun résultat | A_CERTIFIER |
| Environments ciblent `/api` ou ports B4F locaux | `sed -n '1,120p' frontend/src/environments/environment*.ts` | Pas d'URL Backend interne | A_CERTIFIER |
| Services Angular alignés B4F | Revue `frontend/src/app/shared/services` et `frontend/src/app/store` | Un service par domaine B4F | A_CERTIFIER |

### CERT-03 — B4F sans DB ni externe direct

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Aucune migration dans B4F | `find apis/exposed -type d \( -name alembic -o -name versions \)` | Aucun résultat | A_CERTIFIER |
| Aucun accès DB B4F | `rg "DATABASE_URL|create_engine|sessionmaker|declarative_base|metadata\\.create_all|SQLAlchemy|sqlalchemy" apis/exposed -g '*.py'` | Aucun résultat hors tests | A_CERTIFIER |
| Aucun client externe direct en B4F | `rg "graph\\.microsoft|Pipedream|requests\\.|httpx\\.|aiohttp|create_connect_token" apis/exposed -g '*.py'` | Pas d'appel tiers direct; délégation Backend uniquement | A_CERTIFIER |

### CERT-04 — Backend invisible hors cluster

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Aucun Backend dans gateway values | `rg "backend-api" deploy/values frontend/src` | Aucun Backend exposé | A_CERTIFIER |
| Aucun Ingress propre Backend | `rg "ingress|Ingress" deploy/values apis/internal` | Pas de config Ingress Backend projet | A_CERTIFIER |
| Backends accessibles par DNS interne seulement | Revue B4F clients | URLs internes ou variables service internes | A_CERTIFIER |

### CERT-05 — Backend sans HTTP vers Backend

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Aucun appel HTTP vers `*-backend-api` depuis Backend | `rg "httpx|requests|aiohttp|backend-api|\\.svc\\.cluster\\.local" apis/internal -g '*.py'` | Aucun appel Backend->Backend direct | A_CERTIFIER |
| Event bus utilisé pour synchro | `find apis/internal -path '*/events/*' -type f` | Publishers/subscribers présents quand nécessaire | A_CERTIFIER |
| Subscribers idempotents | Revue code subscriber | Upsert, ignore duplicats ou contrôle d'état | A_CERTIFIER |

### CERT-06 — Alembic obligatoire

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Aucun DDL runtime | `rg "metadata\\.create_all|db\\.create_all|SQLModel\\.metadata\\.create_all|drop_all\\(" apis -g '*.py'` | Aucun résultat | A_CERTIFIER |
| Aucun SQL manuel hors Alembic | `find . -name '*.sql' -not -path './.git/*'` | Aucun fichier SQL d'init manuel | A_CERTIFIER |
| DDL seulement en versions Alembic | `rg "CREATE TABLE|CREATE SCHEMA|ALTER TABLE|DROP TABLE|GRANT " apis/internal -g '*.py' -g '!**/alembic/versions/**'` | Aucun résultat hors migrations | A_CERTIFIER |
| Première migration crée schéma et droits | Revue première migration par Backend | `CREATE SCHEMA`, `GRANT`, `ALTER DEFAULT PRIVILEGES` | A_CERTIFIER |

### CERT-07 — Downgrade Alembic

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| `downgrade()` présent | `rg "def downgrade" apis/internal/*-backend-api/alembic/versions/*.py` | Une occurrence par migration | A_CERTIFIER |
| Pas de downgrade vide | `rg "def downgrade[\\s\\S]*?(pass|NotImplementedError)" apis/internal/*-backend-api/alembic/versions/*.py` | Aucun résultat | A_CERTIFIER |
| Symétrie statique | Comparer `create/drop`, `add/drop`, `CREATE/DROP SCHEMA` | Compteurs cohérents par migration | A_CERTIFIER |
| Test réel sur DB jetable | `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` par Backend modifié | Succès local documenté | A_CERTIFIER |

### CERT-08 — PgBouncer compatible

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Pools bornés | `rg "pool_size|max_overflow|pool_pre_ping|pool_recycle" apis/shared apis/internal -g '*.py'` | `pool_size <= 5`, `max_overflow <= 5`, pre-ping, recycle <= 300 | A_CERTIFIER |
| Prepared statements désactivés | `rg "statement_cache_size|prepare_threshold" apis -g '*.py'` | `0` ou `None` selon driver | A_CERTIFIER |
| Pas de `SET search_path` hors transaction | `rg "SET search_path|SET LOCAL" apis/internal -g '*.py'` | Aucun `SET search_path`; `SET LOCAL` seulement encadré | A_CERTIFIER |

### CERT-09 — Redis event bus

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Redis dans compose | `rg "redis|REDIS_URL" docker-compose.yml .env.example deploy/values` | Redis configuré local + values | A_CERTIFIER |
| Payload contient `trace_id` | `rg "trace_id" apis/shared apis/internal -g '*.py'` | Event schema et publishers propagent `trace_id` | A_CERTIFIER |
| B4F ne publish/subscribe pas | `rg "EventBus|publish|subscribe|REDIS_URL" apis/exposed -g '*.py'` | Aucun usage event bus en B4F | A_CERTIFIER |

### CERT-10 — Frontend Angular/NGRX

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Store feature par B4F | `find frontend/src/app/store -maxdepth 2 -type f` | Actions, reducer, effects, selectors par domaine | A_CERTIFIER |
| Effects appellent services | `rg "createEffect|Actions" frontend/src/app/store -g '*.ts'` | Appels HTTP indirects via services | A_CERTIFIER |
| Components sans HTTP direct | `rg "HttpClient|\\.subscribe\\(" frontend/src/app/pages frontend/src/app/components -g '*.ts'` | Aucun HTTP direct non justifié dans composant | A_CERTIFIER |
| Templates critiques avec `async` ou signal store | Revue dashboard/listes/pages touchées | Pas d'état statique manuel pour données B4F | A_CERTIFIER |

### CERT-11 — Routes et gateway

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Gateway unique | `find deploy/values -name 'gateway.yaml' -print` | Gateway par env, pas par API | A_CERTIFIER |
| Frontend route `/` | Revue values gateway/frontend | `/` vers frontend | A_CERTIFIER |
| B4F sur `/api/<service>` | Revue values et env production frontend | Routes vers B4F seulement | A_CERTIFIER |
| Backend sans route publique | `rg "internal/.*backend|backend-api" deploy/values frontend` | Aucun résultat exposé | A_CERTIFIER |

### CERT-12 — Observabilité

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Probes non authentifiées | Appeler `/liveness`, `/readiness`, `/startup`, `/health`, `/metrics` | HTTP 200 ou health `degraded`, jamais auth-required | A_CERTIFIER |
| Logs JSON stdout | `rg "JSONRenderer|structlog|stdout" apis/shared apis -g '*.py'` | Logger structuré centralisé | A_CERTIFIER |
| `traceparent` propagé | `rg "traceparent|x-request-id" apis/shared apis -g '*.py'` | Middleware + client HTTP | A_CERTIFIER |
| OTel/Alloy local | `rg "alloy|OTEL_EXPORTER_OTLP_ENDPOINT" docker-compose.yml .env.example deploy/values` | Config présente | A_CERTIFIER |

### CERT-13 — Secrets et env

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| `.env.example` complet | `sed -n '1,220p' .env.example` | Variables DB, Redis, OTel, API ports | A_CERTIFIER |
| `.env` ignoré | `git check-ignore .env` | `.env` ignoré | A_CERTIFIER |
| Pas de secrets réels | `rg "password|secret|token|apikey|api_key" . -g '!node_modules/**' -g '!frontend/dist/**'` | Aucun secret réel versionné | A_CERTIFIER |
| Variables DB partagées | `rg "DB_HOST|DB_USERNAME|DB_PASSWORD|DB_DATABASE|DATABASE_SSLMODE" .env.example deploy/values` | Variables canoniques présentes | A_CERTIFIER |

### CERT-14 — Développement local

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Wrappers racine | `ls run_all_apis.sh migrate_all_apis.sh run_all_apis_tests.sh run_frontend.sh run_frontend_tests.sh run_frontend_e2e.sh` | Scripts présents et exécutables | A_CERTIFIER |
| Scripts par API | `find apis -mindepth 3 -maxdepth 3 \\( -name run_api.sh -o -name run_tests.sh -o -name migrate.sh \\)` | Scripts uniformes selon type API | A_CERTIFIER |
| Docker local démarre | `docker compose --env-file .env.example up -d --build` | Conteneurs healthy ou justification | A_CERTIFIER |
| Frontend local accessible | `curl -I http://localhost:4700/login` | HTTP 200 | A_CERTIFIER |

### CERT-15 — Clean Architecture

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| 4 couches par API | `find apis -path '*/app/domain' -o -path '*/app/application' -o -path '*/app/infrastructure' -o -path '*/app/presentation'` | Dossiers présents | A_CERTIFIER |
| Domain sans framework | `rg "fastapi|sqlalchemy|pydantic|BaseModel|Column\\(" apis/*/*/app/domain -g '*.py'` | Aucun résultat | A_CERTIFIER |
| Application sans framework | `rg "fastapi|sqlalchemy|pydantic|APIRouter|Depends\\(" apis/*/*/app/application -g '*.py'` | Aucun résultat ou exception documentée | A_CERTIFIER |
| Import-linter | `find apis -name pyproject.toml -exec rg -n "importlinter|contract" {} +` | Contrats présents et verts | A_CERTIFIER |

### CERT-16 — UI et thème

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Cahier UI présent | `test -f Cameleon/cahier-normes-ui-cde-v1.5.md` | Document présent | A_CERTIFIER |
| Matrice UI présente | `test -f Cameleon/matrice-validation-ui-cde-v1.5.md` | Document présent | A_CERTIFIER |
| Boutons primaires noirs, pas de bleu thème | `rg "2F80ED|1f6ed4|EAF3FF|3B82F6|2563EB|DBEAFE" frontend/src/styles.css frontend/src/app/pages/login frontend/src/app/pages/chat frontend/src/app/shared/layout frontend/src/app/pages/dashboard` | Aucun résultat | A_CERTIFIER |
| Captures UI | `find captures -maxdepth 1 -name 'ui-theme-*.png'` | Login, dashboard, conversation, settings, contacts | A_CERTIFIER |

### CERT-17 — Tests locaux

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Build frontend | `cd frontend && npm run build` | Succès; avertissements documentés | A_CERTIFIER |
| Tests API touchées | `./run_all_apis_tests.sh` ou scripts ciblés | Succès ou justification par API | A_CERTIFIER |
| E2E frontend si UI touchée | `./run_frontend_e2e.sh --project=chromium` ou parcours Playwright manuel | Capture et résultat | A_CERTIFIER |
| Login local | Ouvrir `http://localhost:4700/login` + login local | Arrivée sur `/dashboard` | A_CERTIFIER |

### CERT-18 — CI/CD et Harbor

| Critère | Test | Preuve attendue | Statut |
| --- | --- | --- | --- |
| Includes CI partagés | Hors périmètre | Non certifié dans cette passe | SKIP_CI_CD |
| Kaniko + Harbor + verify | Hors périmètre | Non certifié dans cette passe | SKIP_CI_CD |
| Smoke-test deploy | Hors périmètre | Non certifié dans cette passe | SKIP_CI_CD |
| Variables GitLab et runners | Hors périmètre | Non certifié dans cette passe | SKIP_CI_CD |

## Commande de certification recommandée

```bash
# 1. Statique architecture
rg "backend-api|apis/internal|localhost:80(0[7-9]|1[0-9])" frontend/src || true
find apis/exposed -type d \( -name alembic -o -name versions \)
rg "DATABASE_URL|create_engine|sessionmaker|declarative_base|metadata\.create_all|SQLAlchemy|sqlalchemy" apis/exposed -g '*.py' || true
rg "metadata\.create_all|db\.create_all|SQLModel\.metadata\.create_all|drop_all\(" apis -g '*.py' || true
find . -name '*.sql' -not -path './.git/*'

# 2. Alembic
rg "def downgrade" apis/internal/*-backend-api/alembic/versions/*.py
rg "\bpass\b|NotImplementedError" apis/internal/*-backend-api/alembic/versions/*.py || true

# 3. Frontend/UI
cd frontend && npm run build
cd ..
rg "2F80ED|1f6ed4|EAF3FF|3B82F6|2563EB|DBEAFE" frontend/src/styles.css frontend/src/app/pages/login frontend/src/app/pages/chat frontend/src/app/shared/layout frontend/src/app/pages/dashboard || true

# 4. Local runtime
docker compose --env-file .env.example ps
curl -I http://localhost:4700/login
```

## Verdict de certification

| Champ | Valeur |
| --- | --- |
| Verdict | `A_CERTIFIER` |
| Raison | Matrice créée; exécution complète des preuves à faire au prochain audit |
| CI/CD | Exclu (`SKIP_CI_CD`) |
| Prochaine action | Exécuter la commande de certification et remplacer les statuts `A_CERTIFIER` par `OK` ou `VIOLATION` avec preuves |
