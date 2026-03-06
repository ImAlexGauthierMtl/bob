# Template: CRUD Module Clean Architecture — Orchestrateur

> Séquence pour ajouter un module CRUD complet en Clean Architecture.

## Input requis

| Paramètre | Exemple |
|-----------|---------|
| `{Resource}` (PascalCase) | `Client` |
| `{resource}` (snake_case) | `client` |
| `{resources}` (pluriel) | `clients` |

## Séquence Backend

| # | Template | Fichier généré |
|---|---------|---------------|
| 1 | `domain-entity` | `app/domain/entities/{resource}.py` |
| 2 | `model-sqlalchemy` | `app/infrastructure/models/{resource}_model.py` |
| 3 | `schemas-pydantic` | `app/presentation/schemas/{resource}_schemas.py` |
| 4 | `repository-pattern` | `app/infrastructure/persistence/{resource}_repository.py` |
| 5 | `use-case` | `app/application/use_cases/{resource}_use_cases.py` |
| 6 | `router-crud` | `app/presentation/routes/{resource}_routes.py` |
| 7 | `alembic-migration` | `alembic/versions/xxx_add_{resources}.py` |
| 8 | `test-backend-unit` | `tests/unit/test_{resource}_use_cases.py` |
| 9 | `test-backend-integration` | `tests/integration/test_{resources}_endpoints.py` |

## Séquence Frontend

| # | Template | Fichier généré |
|---|---------|---------------|
| 1 | `model-typescript` | `core/models/{resource}.models.ts` |
| 2 | `service-http` | `core/services/{resource}.service.ts` |
| 3 | `store-feature-ngrx` | `store/{resources}/` (actions, reducer, effects, selectors) |
| 4 | `page-list` | `features/{resources}/{resources}-list.component.ts` |
| 5 | `page-detail` | `features/{resources}/{resource}-detail.component.ts` |
| 6 | `component-form` | `features/{resources}/{resource}-form.component.ts` |

## Post-création

1. Enregistrer le router dans `main.py` : `app.include_router({resource}_router)`
2. Ajouter la route dans `app.routes.ts`
3. Ajouter le store dans `provideStore()`
4. Tester : `pytest` + `ng test`

## Différence avec `crud-module` existant

Le `crud-module` existant est simple (1 fichier routes, 1 modèle). Ce template ajoute :
- Couche domaine séparée du modèle ORM
- Use cases avec injection du repository
- Tests unitaires ET intégration
- Frontend complet avec NgRx store
