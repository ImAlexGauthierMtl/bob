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
- 30 fichiers d'entités de domaine importent SQLAlchemy ou déclarent des `Column`/`relationship`.
- plusieurs routes contiennent encore de la logique métier ou de persistence.
- les 17 `pyproject.toml` contiennent des contrats `import-linter` progressifs, validés localement.

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
| `domain/` sans framework | VIOLATION | 30 fichiers `app/domain/entities/*.py` importent SQLAlchemy ou déclarent `Column`/`relationship` |
| `application/` sans framework | OK | scan `application/` pour FastAPI, SQLAlchemy, httpx, redis, pydantic_settings et import `app.presentation`: aucun résultat direct |
| Routes minces | VIOLATION | `activity-backend-api/app/presentation/routes/activity_routes.py` est maintenant mince et passe par `ActivityUseCases`; la violation reste ouverte pour les routes encore épaisses, exemples: `provider_membrane_routes.py`, `training_routes.py`, `auth_routes.py` |
| Entités métier pures | VIOLATION | les entités de domaine dérivent indirectement du modèle SQLAlchemy via `Base` et déclarent leurs colonnes ORM |
| Contrats import-linter | OK | Les 17 `pyproject.toml` configurent 2 contrats progressifs; `lint-imports --config pyproject.toml --no-cache` passe sur les 17 APIs, 34 contrats gardes, 0 brise |

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

## Fichiers d'entités ORM dans `domain/`

Exemples représentatifs:

```text
apis/internal/activity-backend-api/app/domain/entities/activity.py
apis/internal/agent-backend-api/app/domain/entities/capability.py
apis/internal/contact-backend-api/app/domain/entities/contact.py
apis/internal/email-backend-api/app/domain/entities/ms365_connection.py
apis/internal/kb-backend-api/app/domain/entities/kb_article.py
apis/internal/opportunity-backend-api/app/domain/entities/opportunity.py
apis/internal/org-backend-api/app/domain/entities/organization.py
apis/internal/product-backend-api/app/domain/entities/product.py
apis/internal/usage-backend-api/app/domain/entities/usage_transaction.py
apis/internal/user-backend-api/app/domain/entities/user.py
apis/internal/workflow-backend-api/app/domain/entities/workflow.py
```

## Recommandation de conversion suivante

Pour fermer M-10/CA-* sans casser le runtime, faire une passe dédiée par famille d'API:

1. Créer des modèles domaine purs (`dataclass` ou classes Python sans ORM).
2. Déplacer les modèles SQLAlchemy vers `infrastructure/persistence/models`.
3. Ajouter des repositories/ports en `application`.
4. Garder les routes FastAPI limitées à validation HTTP, appel de use case et mapping réponse.
5. Ajouter des contrats import-linter par API avant de déplacer tout le code.
6. Répliquer le pattern validé sur `activity-backend-api` vers `contact-backend-api`, `org-backend-api`, `opportunity-backend-api` et les routes longues `email-backend-api`.
