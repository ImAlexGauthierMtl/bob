---
name: dx_intermediate_create_apis
description: Crée une nouvelle API conforme — soit B4F (apis/exposed/) soit Backend (apis/internal/) — avec son arborescence Clean Architecture, ses scripts run/migrate/test, son intégration event bus, ses migrations Alembic initiales. Sait aussi splitter un monolithe (procédure § 2.8) ou splitter authentication-api en auth-b4f-api + iam-backend-api. À invoquer pour ajouter une API au projet.
metadata:
  reference: § 2 + § 12 (Clean Archi) de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_create_apis

## Paramètres requis

Avant de créer, l'agent doit confirmer :
1. **Tier** : `b4f` ou `backend`
2. **Nom du service** (slug, ex. `rooms`, `front-office`, `iam`)
3. **Entité principale** (pour un Backend) : ex. `rooms`, `clients`. Doit avoir
   un CRUD complet (§ 2.3).
4. **Domaine frontend** (pour un B4F) : ex. `front-office`. Doit correspondre à
   une section UI.
5. **Le repo central** existe-t-il ? Si non → invoquer `dx_intermediate_create_cicd_repo` AVANT.

Refuser de créer une API nommée `authentication` ou contenant `auth*entication*`
(§ 2.5). Proposer le split.

## Workflow

### Pour un Backend API

1. Créer `apis/internal/<service>-backend-api/` avec la structure Clean Archi
   (cf. § 12.2) :
   - `domain/` (entities, value_objects, exceptions, ports)
   - `application/` (use_cases, dtos)
   - `infrastructure/` (persistence, messaging, config)
   - `presentation/` (api/v1, deps, main, exception_handlers, **endpoints de santé** § 5.10)
2. Invoquer `dx_base_create_api_backend_scaffold` (génère squelette + pyproject)
3. Invoquer `dx_base_create_api_migration_initial` pour la première migration
   qui crée le schéma `<service>` + tables initiales (§ 2.7.2)
4. Inclure `migrate_with_lease.py` via le repo central (pas dupliquer)
5. Pool SQLAlchemy conforme (§ 2.7.3) : `pool_size=3`, `max_overflow=3`,
   `pool_pre_ping=True`, `pool_recycle=300`, `statement_cache_size=0`
6. Event bus Redis (§ 2.4) : publisher + subscriber dans `infrastructure/messaging/`
7. Scripts `run_api.sh`, `migrate.sh`, `run_tests.sh` (§ 11.2)
8. Values Helm dans `deploy/values/{dev,staging,prod}/<service>-backend-api.yaml`
   - **Pas d'ingress**
   - InitContainer migrate
   - Probes (`/liveness`, `/readiness`, `/startup`)
   - `OTEL_*` injectées par le chart
9. `Dockerfile` multi-stage, image distroless ou slim, USER non-root (§ 4.10)

### Pour un B4F API

1. Créer `apis/exposed/<service>-b4f-api/` avec la structure Clean Archi
   - `domain/` (models = interfaces, exceptions, ports)
   - `application/` (use_cases avec agrégation, filtrage, validation)
   - `infrastructure/` (backends/ — clients HTTP vers les Backend ; auth/, config)
   - `presentation/` (api/v1, deps, main, **endpoints de santé** § 5.10)
2. **Aucun `alembic/`, modèle SQLAlchemy, `DATABASE_URL`** — c'est interdit
3. Aucun appel direct à un service externe — déléguer au Backend
4. Scripts `run_api.sh`, `run_tests.sh` (pas `migrate.sh`)
5. Values Helm avec **ingress activé** sur `/<service>`
6. `/health` liste les Backend appelés + auth comme dépendances (§ 5.10)

### Pour un split de monolithe (procédure § 2.8)

Ordre obligatoire :
1. Créer la Backend en premier (héritage du schéma DB, migration non destructive)
2. Créer la B4F qui appelle la Backend
3. Mettre à jour la gateway pour pointer la B4F
4. Mettre à jour la config frontend
5. Décommissionner l'ancien monolithe

**Aucune migration destructive pendant le split.** L'historique `versions/`
Alembic est transféré intact.

### Cas spécifique : authentication-api

Split obligatoire (§ 2.5). Schéma DB renommé `authentication` → `iam` via une
migration (modèle fourni dans la doc). Tables renommées
`authentication_users` → `iam.users` etc.

## Base skills

- `dx_base_create_api_b4f_scaffold`
- `dx_base_create_api_backend_scaffold`
- `dx_base_create_api_migration_initial`
- `dx_base_create_api_split_authentication`
- `dx_base_create_split_responsibilities_b4f_backend` — remonte la logique d'affaire au B4F, redescend l'infra aux Backend atomiques (v1.7)

### Alembic strict (v1.2)

- `dx_base_create_alembic_first_revision_with_schema` — première révision avec CREATE SCHEMA + DROP SCHEMA CASCADE en downgrade
- `dx_base_create_alembic_migration_with_downgrade` — nouvelle révision avec upgrade ET downgrade (refus si downgrade vide)
- `dx_base_create_alembic_convert_sql_file` — convertir un init.sql / seed.sql artisanal en révision Alembic
- `dx_base_create_alembic_run_tests_with_downgrade` — run_tests.sh teste upgrade → downgrade → upgrade

Pour plusieurs APIs en même temps, **paralléliser via subagents** (un par API,
chaque sous-dossier est indépendant).

## Anti-patterns

1. Créer une B4F avec un dossier `alembic/` "pour plus tard"
2. Créer une Backend sans pré-créer le schéma `<service>` dans la première migration
3. Oublier les 5 endpoints de santé (§ 5.10)
4. Hardcoder un port — toujours `<API_PREFIX>_PORT` (§ 11.4)
5. Réutiliser le terme `authentication` — banni
6. Mettre `migrate_with_lease.py` dans chaque API — il vit dans le repo central
7. **Générer une migration avec `def downgrade(): pass`** — refus systématique (§ 2.7.5)
8. **Mettre un fichier `.sql` dans le repo** plutôt qu'une révision Alembic — refus (§ 2.7.5)
