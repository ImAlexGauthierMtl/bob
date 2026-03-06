# Template: Auth Module Fullstack — Orchestrateur

> Séquence exacte pour implémenter l'authentification complète backend + frontend.

## Séquence d'exécution (ordre strict)

### Étape 1 — Backend `auth-api`

| # | Template à utiliser | Résultat |
|---|-------------------|----------|
| 1 | `api-bootstrap` | `main.py`, `requirements.txt`, `Dockerfile` |
| 2 | `domain-entity` | `app/domain/entities/user.py` |
| 3 | `schemas-pydantic` | `app/presentation/schemas/auth_schemas.py` |
| 4 | `database-config` | `app/infrastructure/database.py` |
| 5 | `repository-pattern` | `app/infrastructure/persistence/user_repository.py` |
| 6 | `auth-jwt` | Routes + use cases (login, register, refresh, logout, me) |
| 7 | `alembic-migration` | `alembic/` + migration initiale users |
| 8 | `seed-data` | `seed.py` (superadmin) |
| 9 | `test-backend-unit` | `tests/unit/` |
| 10 | `test-backend-integration` | `tests/integration/` |

### Étape 2 — Frontend Angular

| # | Template à utiliser | Résultat |
|---|-------------------|----------|
| 1 | `model-api` | `core/models/auth.models.ts` |
| 2 | `service-cookie` | `core/services/cookie.service.ts` |
| 3 | `service-auth` | `core/services/auth.service.ts` |
| 4 | `auth-guard` | `core/guards/auth.guard.ts` |
| 5 | `guest-guard` | `core/guards/guest.guard.ts` |
| 6 | `interceptor-auth` | `core/interceptors/auth.interceptor.ts` |
| 7 | `interceptor-snake-case` | `core/interceptors/snake-case-response.interceptor.ts` |
| 8 | `store-feature-ngrx` | `store/auth/` (actions, reducer, effects, selectors) |
| 9 | `layout-main` | `layout/` (main-layout + auth-layout + sidebar + header) |
| 10 | `page-login` | `pages/public/login/login.component.ts` |
| 11 | `environment-config` | `environments/` + `proxy.conf.json` |

### Étape 3 — Configuration

| # | Action | Détails |
|---|--------|---------|
| 1 | CORS | Backend : origins = `["http://localhost:4200"]` |
| 2 | Proxy | `proxy.conf.json` : `/api/v1/auth` → `localhost:8001` |
| 3 | Docker | `docker-compose.yml` : database + auth-api |

## Vérification

```bash
# Backend
cd apis/auth-api && pytest
# Frontend
cd frontend && ng test
# E2E : naviguer vers /auth/login, se connecter, vérifier redirect
```
