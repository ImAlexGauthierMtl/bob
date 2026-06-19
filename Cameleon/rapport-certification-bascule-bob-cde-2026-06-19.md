# Rapport certification bascule Bob CDE

Date: 2026-06-19
Projet: Croo Digital Experience
Branche: `refactor/bob-cde-local-rbac-cloud-contract`
Reference: `Cameleon/matrice-certification-regles-architecture-v1.5.md`

## Verdict perimetre Bob

Statut: PASS perimetre Bob / Agent Control / Bob Chat / Bob Cloud local.

Ce rapport ne certifie pas toutes les dettes historiques globales du repo. Il
certifie la bascule Bob traitee dans les slices 36, 37 et 38:

- extraction source `agent-control-b4f-api`;
- retrait source/runtime actif `ai-agent-b4f-api`;
- routing Bob Chat et Agent Control vers B4F dediees;
- gestion locale CDE tenants/licences/RBAC sans Bob Cloud reel;
- smoke UI local mocke de login, dashboard et Platform Access.

## Preuves

### Agent Control B4F

- `./run_all_apis_tests.sh agent-control-b4f-api`
  - 13 tests passent;
  - couverture 99.09%;
  - JUnit: `apis/exposed/agent-control-b4f-api/junit.xml`.
- Certification independante:
  - PASS 9/10;
  - aucun P0/P1/P2/P3 bloquant.
- `AGENT_BACKEND_API_URL` est exige explicitement.
- `CDE_LOCAL_AGENT_CONTROL_CAPABILITIES` est vide par defaut dans
  `.env.example` et `docker-compose.yml`.

### Retrait ai-agent actif

- `apis/exposed/ai-agent-b4f-api` absent du filesystem.
- Scan actif hors archives v1.4 et docs de migration:
  - aucun `ai-agent-b4f-api`;
  - aucun `ai_agent_b4f_api`;
  - aucun `AI_AGENT`;
  - aucun `ai-agent~b4f-api`.
- Certification independante:
  - PASS 9.5/10;
  - anciens artefacts ignores nettoyes apres certification.

### Bob Chat, Bob Cloud local et Platform Settings

- `./run_all_apis_tests.sh bob-chat-b4f-api`
  - 20 tests passent;
  - couverture 89.18%.
- `./run_all_apis_tests.sh bob-cloud-stub-api`
  - 10 tests passent;
  - couverture 98.47%.
- `./run_all_apis_tests.sh platform-b4f-api`
  - 20 tests passent;
  - couverture 97.25%.
- `PYTHONPATH=apis ... pytest apis/shared/tests -q --junitxml=test-reports/shared-junit.xml`
  - 20 tests passent;
  - JUnit shared dedie produit.

### Frontend

- `npm run build` dans `frontend`
  - succes;
  - warnings Angular/budgets/CommonJS preexistants.
- Smoke local mocke sur `127.0.0.1:4701`:
  - `captures/cde-bascule-login-2026-06-19.png`;
  - `captures/cde-bascule-dashboard-2026-06-19.png`;
  - `captures/cde-bascule-platform-access-2026-06-19.png`;
  - aucune erreur console finale.

## Architecture

Conformite perimetre Bob:

- Frontend appelle des B4F nommees:
  - `bob-chat-b4f-api`;
  - `agent-control-b4f-api`;
  - `platform-b4f-api` pour Bob Settings.
- Agent Control B4F ne contient pas DB, Alembic, Redis pub/sub ou provider
  externe direct.
- Bob Chat et Agent Control supportent les chemins gateway publics et internes
  reecrits.
- `docs/ARCHITECTURE.md` ne montre plus de flux B4F vers services externes;
  MS365 et enrichment partent des backends.

## Limites restantes hors certification Bob

- La matrice globale v1.5 reste a executer end-to-end avant MR finale.
- Le smoke effectue est local et mocke; un smoke production-ready devra tourner
  avec les APIs live et Bob Cloud reel ou staging.
- Le frontend CDE ne stocke plus de jeton auth navigateur et consomme la session
  via cookie Bob Cloud/stub (`/api/auth/v1/session|refresh|logout`).
- Smoke cookie local valide: `consoleErrors: []`, `localStorageKeys: []`,
  captures `cde-auth-cookie-login-2026-06-19.png`,
  `cde-auth-cookie-dashboard-2026-06-19.png` et
  `cde-auth-cookie-platform-access-2026-06-19.png`.
- `auth-b4f-api` revalide: 11 tests passent, couverture 93.98%.
- Le smoke effectue reste local/mocke; un smoke staging avec Bob Cloud reel doit
  confirmer les cookies cross-domain, expirations et refus session.
- Les mentions LibreChat restantes sont dans les documents de migration,
  matrices et revues, pas dans le runtime visible.

## Decision

La bascule Bob locale CDE peut continuer vers la phase de stabilisation finale.
Ne pas declarer production-ready tant que la matrice globale et le smoke live
staging avec Bob Cloud reel ne sont pas termines.
