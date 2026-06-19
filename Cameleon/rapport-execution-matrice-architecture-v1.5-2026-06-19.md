# Rapport d'execution matrice architecture CDE v1.5

Date: 2026-06-19
Branche: `refactor/bob-cde-local-rbac-cloud-contract`
Decision: certification locale accordee hors CI/CD; preuve staging/Bob Cloud reel a executer separement.

## Synthese

La bascule Bob/CDE locale respecte le modele attendu: Angular consomme des B4F,
Bob Cloud reel est remplace localement par `bob-cloud-stub-api`, les tenants,
licences, users, roles et memberships sont visibles et gerables dans
`Settings > Platform Access`, et la session frontend passe par cookie
Bob Cloud/stub sans token auth brut en navigateur.

La matrice globale v1.5 est passante en local, hors perimetre CI/CD marque
`SKIP_CI_CD`. La preuve staging/Bob Cloud reel reste a executer separement
avec l'equipe plateforme.

## Preuves passantes

| Controle | Resultat |
|---|---|
| Source de verite | `docs/regles-architecture-deploiement.md` present |
| Livrables Cameleon | matrices, audits, cahiers UI et rapports presents |
| Structure B4F | 7 B4F sous `apis/exposed` |
| Structure Backends | 14 Backends sous `apis/internal` |
| B4F sans Alembic | `find apis/exposed ... alembic/versions` sans resultat |
| B4F sans DB | scan SQLAlchemy/DDL sur `apis/exposed` sans resultat hors tests |
| Backend non expose gateway | aucun `backend-api` dans `deploy/values/*/gateway.yaml` |
| DDL runtime | aucun `metadata.create_all`, `db.create_all` ou `drop_all` hors tests |
| SQL init manuel | aucun fichier `.sql` projet hors dependances ignorees |
| Downgrades Alembic | `def downgrade` present dans toutes les migrations scannees |
| Downgrade vide | aucun `pass` ou `NotImplementedError` dans les downgrades |
| PgBouncer | pool borne, `pool_pre_ping=True`, recycle 300, `prepare_threshold=None` |
| Redis/event bus | `REDIS_URL`, service Redis Compose et values deploy presents |
| Observabilite | `structlog`, JSON renderer, stdout, `traceparent`, `x-request-id`, Alloy/OTLP presents |
| Gateway | gateways dev/staging/prod uniques; Bob publie `agent-control`, `bob-settings`, `bob-chat` |
| Build frontend | `npm run build` passe avec warnings historiques |
| Wrapper API global | `./run_all_apis_tests.sh`: passed=22 failed=0 skipped=0 |
| Wrapper API global avec Alembic DB | `DATABASE_URL=postgresql+psycopg2://...@localhost:55432/... ./run_all_apis_tests.sh`: passed=22 failed=0 skipped=0; sortie persistée dans `test-reports/run_all_apis_tests-with-alembic-2026-06-19.log` |
| Auth B4F | `./run_all_apis_tests.sh auth-b4f-api`: 11 passes, couverture 93.98% |
| Naming auth | scan `rg "authentication" apis frontend deploy ...` sans resultat |
| Pages sans HTTP direct | scan `rg "HttpClient" frontend/src/app/pages` sans resultat |
| B4F sans EventBus | scan `rg "EventBus|publish|subscribe|REDIS_URL|event_bus" apis/exposed ...` sans resultat hors tests |
| Backend sans HTTP Backend->Backend | scan `rg "create_service_client|backend-api|\\.svc\\.cluster\\.local" apis/internal ...` sans resultat hors tests |
| Email Backend | `./run_all_apis_tests.sh email-backend-api`: 12 passes, couverture 87.17%; Alembic saute explicitement sans DB locale configuree |
| Smoke UI | Playwright local: login, dashboard, Platform Access; `consoleErrors: []`, `localStorageKeys: []` |
| Captures UI | `captures/cde-auth-cookie-login-2026-06-19.png`, `captures/cde-auth-cookie-dashboard-2026-06-19.png`, `captures/cde-auth-cookie-platform-access-2026-06-19.png` |
| Certification indépendante | Subagent Feynman: score final 9.5/10, verdict local PASS hors CI/CD; aucune non-conformité code bloquante |

## Corrections appliquees pendant l'execution

| Reserve | Correction |
|---|---|
| CERT-01 | Mentions runtime/commentaires `authentication` remplacees par `auth`; scan propre. |
| CERT-10 | Appels usage de `tenant-detail` et `usage-logs` deplaces dans `frontend/src/app/shared/services/usage.service.ts`; scan `HttpClient` sur pages propre; build frontend OK. |
| CERT-09 | Placeholder `WorkflowEventBus` retire de `communication-b4f-api`; les webhooks B4F acceptent la requete sans publier, l'execution restant a porter par `workflow-backend-api`. |
| CERT-05 | Self-call HTTP `email-backend-api -> email-backend-api` remplace par des adapters locaux sur repositories/use cases; scan Backend HTTP propre. |
| CERT-17 | Scripts Backends historiques et nouveaux Backends Bob alignes; Alembic s'execute si `DATABASE_URL`/`DB_*` est configure, sinon skip explicite local avant pytest. Wrapper global passe 22/22 avec et sans DB jetable. |

## Reserves globales detectees

| ID matrice | Niveau | Reserve | Evidence |
|---|---|---|---|
| CI/CD | SKIP_CI_CD | CI/CD, Harbor, registry, runners et variables GitLab restent hors perimetre actif selon la matrice. | `Cameleon/matrice-certification-regles-architecture-v1.5.md` |
| Staging Bob Cloud reel | EXTERNE | Le smoke avec Bob Cloud reel/staging reste a coordonner avec l'equipe Bob Cloud; le stub local est prouve. | `project-x/07-final/rapport-transmission-equipe-bob-cloud-2026-06-19.md` |

## Faux positifs ou exceptions acceptees

| Controle | Justification |
|---|---|
| Frontend local ports 8007/8008 | Ce sont des ports B4F locaux (`bob-chat-b4f-api`, `agent-control-b4f-api`), pas des Backends internes. |
| `httpx` dans B4F Bob | Utilise pour B4F vers Backends internes ou exception Bob Cloud Auth/IAM/licences documentee dans `docs/regles-architecture-deploiement.md`. |
| Scan secrets | Les resultats vus sont exemples docs/tests, enum `INPUT_TOKEN/OUTPUT_TOKEN`, ou variables env sans valeur secrete reelle. |

## Decision

- Perimetre Bob local: PASS avec preuves.
- Matrice locale CDE v1.5: PASS hors CI/CD explicitement exclu.
- Certification indépendante finale: PASS local, score 9.5/10; le point
  restant est externe au code local: smoke Bob Cloud reel/staging et CI/CD.
- Avant bascule staging/prod: executer le smoke contre Bob Cloud reel et la
  chaine CI/CD plateforme.
