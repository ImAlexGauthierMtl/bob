# Rapport final de conversion CDE v1.4

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Branche finale: `refactor/cde-v14-final-integration-docker-local`
Source de vérité: `docs/regles-architecture-deploiement.md`
Matrice: `Cameleon/matrice-validation-conformite-v1.4.md`

## Revue Architecture & Déploiement

### Architecture APIs

OK: les APIs sont alignées sur le modèle deux tiers vérifiable localement.

Preuves:
- `apis/exposed/` porte les B4F et `apis/internal/` porte les Backends.
- Les B4F n'ont pas de dossier Alembic ni de connexion DB directe.
- Le frontend ne cible pas les Backends internes.
- Les intégrations MS365/Membrane ont été déplacées côté `email-backend-api`.
- Les Backends utilisent Redis events au lieu d'appels HTTP Backend->Backend.

### Frontend NGRX

VIOLATION à corriger: la fondation NGRX par B4F est en place, mais la migration n'est pas complète.

Preuves:
- `frontend/src/app/store/{auth,crm,communication,ai-agent,platform,kb}` existe.
- Les nouvelles compositions B4F passent par services + effects.
- Le dashboard est migre vers `loadCrmDashboard` -> `CrmEffects` -> `CrmB4fService`, avec template `vm$ | async` et sans `.subscribe()`.
- Les lectures de listes CRM `organizations`, `contacts`, `opportunities` et `activities` passent maintenant par `CrmEffects` -> `CrmB4fService`; les workflows de creation/search/enrich restent legacy pour une passe suivante.
- Le contrat `crm-b4f-api /dashboard/summary` utilise maintenant les statuts opportunite ouverts valides au lieu de `OPEN`.
- Il reste des pages legacy avec appels/services/subscriptions hors Effects, suivies par `M-03`, `F-03` et `F-04`.
- Docker local sert le frontend sur `http://localhost:4700`.
- Capture locale: `captures/cde-docker-local-home.png`.
- Capture dashboard NgRx: `captures/cde-dashboard-ngrx.png`.
- Captures listes CRM NgRx: `captures/m03-organizations-list.png`, `captures/m03-contacts-list.png`, `captures/m03-opportunities-list.png`, `captures/m03-activities-list.png`.

### Pipeline CI/CD

SKIP_CI_CD: hors périmètre actif à la demande du user.

Preuves:
- Aucun suivi CI/CD ajouté dans cette phase finale.
- Les règles CI/CD restent marquées `SKIP_CI_CD` dans la matrice.

### Configuration K8s

OK: le repo est aligné sur les validations repo-locales disponibles.

Preuves:
- Les values gardent le gateway comme point d'entrée.
- Les routes publiques ciblent le frontend et les B4F, pas les Backends.
- Les Backends déclarent l'initContainer de migration avec Lease/RBAC via le chart partagé.
- Les namespaces et variables plateforme directes restent hors suivi CI/CD.

### Scoping variables

OK: `.env.example` et `docker-compose.yml` permettent un montage local sans collisions courantes.

Preuves:
- Ports locaux ajustés: frontend `4700`, Postgres `55432`, PgBouncer `56432`, Alloy `12346`, OTel `14317/14318`.
- Secrets réels non versionnés; valeurs locales explicitement de développement.
- `docker compose --env-file .env.example config --quiet` passe.

### Registry vers K8s

SKIP_CI_CD: Harbor, registry, robot accounts, Cosign et image promotion sont exclus de cette passe.

Preuves:
- Les lignes Harbor/registry sont marquées `SKIP_CI_CD`.
- Aucun changement registry n'a été introduit dans la branche finale.

### Conventions projet

OK: les artefacts de conversion demandés vivent dans `Cameleon/`, avec la source officielle dans `docs/`.

Preuves:
- `Cameleon/plan-refactor-cde-normes-v1.4.md`.
- `Cameleon/matrice-validation-conformite-v1.4.md`.
- `Cameleon/rapport-final-conversion-v1.4.md`.
- `Cameleon/skills/*/SKILL.md` contient 8 skills de validation.
- Aucun dossier d'ancien outil spécifique interdit actif.

### Observabilité

OK: les APIs exposent les endpoints opérationnels et la trace est propagée.

Preuves:
- `/health`, `/readiness`, `/liveness`, `/startup`, `/metrics` présents via la couche partagée.
- Logs JSON avec `trace_id/request_id`.
- HTTP client partagé propage `traceparent`.
- Redis event bus porte `trace_id`.
- Alloy est présent dans Docker local.

### Développement local

OK: Docker local est monté et validé.

Preuves:
- `docker compose --env-file .env.example up -d --build` terminé.
- 11 Backends internes healthy: ports `9001` à `9011`.
- 6 B4F healthy: ports `8001` à `8006`.
- Frontend accessible: `http://localhost:4700` retourne `HTTP/1.1 200 OK`.
- PgBouncer en mode transaction fonctionne sur `localhost:56432`.
- Les migrations Alembic locales ont été exécutées avec succès: `completed=11`.
- Le runtime DB applique `SET LOCAL search_path` par API pour respecter les schémas Alembic avec PgBouncer.

### Structure interne (Clean Archi + SOLID)

VIOLATION à corriger: la séparation stricte des couches n'est pas encore complète.

Preuves:
- Les 17 APIs ont maintenant les 4 couches uniformes `domain/application/infrastructure/presentation`.
- Les 17 `pyproject.toml` ont 3 contrats import-linter progressifs; validation locale: 51 contrats gardes, 0 brise.
- `membrane_tenant_key_service.py` retire une dependance `application -> presentation` dans `email-backend-api`.
- `activity-backend-api` a une extraction verticale: les routes appellent `ActivityUseCases`, la dépendance FastAPI/repository est isolée dans `presentation/deps.py`, et le contrat local passe.
- Les modèles SQLAlchemy résident maintenant dans `app/infrastructure/persistence/models`; `app/domain` ne contient plus de dépendance SQLAlchemy/Pydantic détectée.
- Certaines routes contiennent encore de la logique métier.
- Le test contractuel email passe, mais `email-backend-api/run_tests.sh` reste bloque localement avant pytest sur un `DATABASE_URL` de migration avec driver placeholder.

### Repo cicd-templates

SKIP_CI_CD: hors périmètre actif à la demande du user.

Preuves:
- Aucun changement de template CI/CD dans la branche finale.
- La matrice conserve les validations CI/CD en `SKIP_CI_CD`.

### Frontend Clean Architecture

VIOLATION à corriger: la migration frontend vers NGRX/Effects est partielle.

Preuves:
- Les nouvelles features B4F sont présentes.
- Les pages legacy gardent encore des patterns directs hors store.
- Le frontend compile et sert en Docker local après renouvellement du volume `node_modules`.

### Fusion branches

OK: les branches de conversion locales sont incluses dans la branche finale.

Preuve:
- Commande de contrôle: `git merge-base --is-ancestor <branche> HEAD`.
- Résultat: 39 branches `refactor/cde-v14-*` vérifiées comme `included`.
- La branche finale contient la pile jusqu'à `refactor/cde-v14-local-clean-architecture-audits`, puis les correctifs Docker local.

### Résumé

- Violations critiques actives: 0.
- Violations à corriger: 2 familles principales.
- Points conformes: architecture APIs, Alembic/DB, K8s repo-local, variables, observabilité, développement local, conventions, rapport final.
- Points exclus volontairement: CI/CD et Harbor/registry.

Violations restantes:
- `M-03`: frontend NGRX partiel, composants/pages legacy à migrer.
- `M-10`: Clean Architecture stricte incomplète.

### Variables CI/CD à créer/modifier dans GitLab

| Variable | Scope | Valeur attendue |
|---|---|---|
| N/A | N/A | CI/CD volontairement hors périmètre actif |
