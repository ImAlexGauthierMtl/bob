# Audit dev local, secrets et Clean Architecture v1.4

Date: 2026-06-18
Projet: Croo Digital Experience (`app-cde-dev-01`)
Source de vérité: `docs/regles-architecture-deploiement.md`
Périmètre: validation repo-locale seulement. CI/CD, Harbor et registry restent exclus volontairement.

## Résumé exécutif

Le périmètre local/dev est conforme aux règles applicables:

- `.env` est ignoré par Git et `.env.example` est versionné.
- `docker compose --env-file .env.example config --quiet` passe.
- les scripts racine et scripts par API existent.
- aucune référence aux anciens outils/projets exclus n'est présente dans le dépôt.
- aucun pattern évident de secret réel suivi par Git n'a été détecté.

La Clean Architecture stricte progresse, mais n'est pas encore conforme:

- les 17 APIs ont maintenant les quatre couches `domain`, `application`, `infrastructure`, `presentation`.
- `activity-backend-api` possède une première extraction verticale: routes HTTP minces, dépendance FastAPI isolée dans `presentation/deps.py`, et logique CRUD/orchestration dans `application/use_cases/activity_use_cases.py`.
- `product-backend-api`, `contact-backend-api`, `org-backend-api`, `opportunity-backend-api` et `user-backend-api` suivent le même pattern de routes HTTP minces avec use cases applicatifs.
- les modèles SQLAlchemy ont été déplacés de `domain/entities` vers `infrastructure/persistence/models`.
- plusieurs routes contiennent encore de la logique métier ou de persistence.
- les 17 `pyproject.toml` contiennent trois contrats `import-linter` progressifs, validés localement.

## Validation dev local et secrets

| Contrôle | Statut | Preuve |
|---|---|---|
| `.env` non versionné | OK | `git ls-files .env` ne retourne rien; `git check-ignore -v .env` pointe vers `.gitignore:29:.env` |
| `.env.example` versionné | OK | `git ls-files .env.example` retourne `.env.example` |
| Secrets évidents suivis par Git | OK | Scan Git sur clés privées, tokens GitHub/OpenAI/Slack/AWS: aucun résultat |
| Références interdites aux anciens outils/projets exclus | OK | scan texte sans résultat hors documentation de l'audit |
| Compose local valide | OK | `docker compose --env-file .env.example config --quiet` passe |
| Secrets Kubernetes | OK | les values utilisent `secretRefs`, pas de valeurs secrètes en clair |
| Secret local de développement | OK | `docker-compose.yml` utilise `dev-only-secret-not-for-production` comme fallback local explicite |
| Documentation locale | OK | seuls `AGENTS.md`, `README.md`, `frontend/README.md` et `apis/shared/requirements.txt` existent hors `docs/`/`Cameleon/`; ces fichiers sont des conventions racine ou des manifests techniques |

## Validation Clean Architecture

| Contrôle | Statut | Preuve |
|---|---|---|
| Quatre couches uniformes par API | OK | Les 17 APIs ont maintenant les couches `domain`, `application`, `infrastructure` et `presentation`; les couches ajoutees sont des packages vides servant de garde-fou avant les refactors verticaux |
| `domain/` sans framework | OK | scan `app/domain` pour SQLAlchemy, FastAPI, Pydantic, `Column` et `relationship`: aucun résultat |
| `application/` sans framework | OK | scan `application/` pour FastAPI, SQLAlchemy, httpx, redis, pydantic_settings et import `app.presentation`: aucun résultat direct |
| Routes minces | VIOLATION | `activity-backend-api/app/presentation/routes/activity_routes.py`, `product-backend-api/app/presentation/routes/product_routes.py`, `contact-backend-api/app/presentation/routes/contact_routes.py`, `org-backend-api/app/presentation/routes/organization_routes.py`, `org-backend-api/app/presentation/routes/department_routes.py`, `opportunity-backend-api/app/presentation/routes/opportunity_routes.py`, `opportunity-backend-api/app/presentation/routes/quote_routes.py`, `user-backend-api/app/presentation/routes/user_routes.py`, `user-backend-api/app/presentation/routes/tenant_routes.py` et `user-backend-api/app/presentation/routes/role_routes.py` sont maintenant minces et passent par des use cases; la violation reste ouverte pour les routes encore épaisses, exemples: `provider_membrane_routes.py`, `training_routes.py`, `auth_routes.py` |
| Entités métier pures | OK | les modèles ORM résident sous `app/infrastructure/persistence/models`; `app/domain/entities` ne contient plus de classes SQLAlchemy |
| Contrats import-linter | OK | Les 17 `pyproject.toml` configurent 3 contrats progressifs; `lint-imports --config pyproject.toml --no-cache` passe sur les 17 APIs, 51 contrats gardes, 0 brise |

## API avec quatre couches

```text
apis/exposed/ai-agent-b4f-api: domain application infrastructure presentation
apis/exposed/auth-b4f-api: domain application infrastructure presentation
apis/exposed/communication-b4f-api: domain application infrastructure presentation
apis/exposed/crm-b4f-api: domain application infrastructure presentation
apis/exposed/kb-b4f-api: domain application infrastructure presentation
apis/exposed/platform-b4f-api: domain application infrastructure presentation
apis/internal/activity-backend-api: domain application infrastructure presentation
apis/internal/agent-backend-api: domain application infrastructure presentation
apis/internal/contact-backend-api: domain application infrastructure presentation
apis/internal/email-backend-api: domain application infrastructure presentation
apis/internal/kb-backend-api: domain application infrastructure presentation
apis/internal/opportunity-backend-api: domain application infrastructure presentation
apis/internal/org-backend-api: domain application infrastructure presentation
apis/internal/product-backend-api: domain application infrastructure presentation
apis/internal/usage-backend-api: domain application infrastructure presentation
apis/internal/user-backend-api: domain application infrastructure presentation
apis/internal/workflow-backend-api: domain application infrastructure presentation
```

## Modèles ORM déplacés vers `infrastructure/`

Exemples représentatifs:

```text
apis/internal/activity-backend-api/app/infrastructure/persistence/models/activity.py
apis/internal/agent-backend-api/app/infrastructure/persistence/models/capability.py
apis/internal/contact-backend-api/app/infrastructure/persistence/models/contact.py
apis/internal/email-backend-api/app/infrastructure/persistence/models/ms365_connection.py
apis/internal/kb-backend-api/app/infrastructure/persistence/models/kb_article.py
apis/internal/opportunity-backend-api/app/infrastructure/persistence/models/opportunity.py
apis/internal/org-backend-api/app/infrastructure/persistence/models/organization.py
apis/internal/product-backend-api/app/infrastructure/persistence/models/product.py
apis/internal/usage-backend-api/app/infrastructure/persistence/models/usage_transaction.py
apis/internal/user-backend-api/app/infrastructure/persistence/models/user.py
apis/internal/workflow-backend-api/app/infrastructure/persistence/models/workflow.py
```

## Recommandation de conversion suivante

Pour fermer M-10/CA-* sans casser le runtime, faire une passe dédiée par famille d'API:

1. Ajouter des use cases/ports en `application`.
2. Garder les routes FastAPI limitées à validation HTTP, appel de use case et mapping réponse.
3. Répliquer le pattern validé sur `activity-backend-api`, `product-backend-api`, `contact-backend-api`, `org-backend-api`, `opportunity-backend-api` et `user-backend-api` vers les routes longues `email-backend-api`, `agent-backend-api`, `usage-backend-api` et `auth-b4f-api`.
4. Renforcer ensuite les contrats import-linter quand les dépendances `application -> infrastructure` restantes auront été extraites derrière des ports.
