# 🔧 Backlog — Templates Backend Manquants

> Patterns backend identifiés dans **ASQ-CRM**, **Madysta ERP**, **Le Baluchon** qui n'ont PAS de template HDQ.
> Chaque entrée = 1 template à créer dans `templates/code/backend/`.

---

## 🔴 Priorité HAUTE — Bloquants pour tout nouveau projet

### 1. `api-bootstrap` — Initialisation d'une API FastAPI
- **Pattern** : `main.py` + CORS + middleware + lifespan events
- **Vu dans** : Toutes les APIs des 3 projets
- **Fichiers** : `main.py`, `requirements.txt`, `Dockerfile`, `run_api.sh`
- **Détails** : Inclut enregistrement des routers, startup/shutdown events, structured logging, exception handlers globaux

### 2. `auth-jwt` — Authentification JWT complète
- **Pattern** : Login/register/refresh/logout avec bcrypt + JWT httpOnly cookies
- **Vu dans** : Madysta `auth-api`, Baluchon `authentication-api`
- **Fichiers** : `routes/auth.py`, `services/auth_service.py`, `schemas/auth.py`, `models/user.py`, `models/session.py`
- **Détails** : Access token + refresh token, middleware de vérification, DI du service auth

### 3. `use-case` — Use Case (Clean Architecture)
- **Pattern** : Couche application avec use cases injectés
- **Vu dans** : Madysta (toutes APIs), Baluchon (toutes APIs)
- **Fichiers** : `app/applications/use_cases/{resource}_use_cases.py`
- **Détails** : Injection du repository, validation métier, séparation présentation/domaine/infrastructure

### 4. `repository-pattern` — Repository (persistence)
- **Pattern** : Abstraction d'accès aux données avec SQLAlchemy
- **Vu dans** : Madysta `infrastructure/persistence/`, Baluchon `infrastructure/repositories/`
- **Fichiers** : `app/infrastructure/persistence/{resource}_repository.py` ou `app/infrastructure/repositories/{resource}_repository.py`
- **Détails** : Interface abstraite + implémentation SQLAlchemy, query builders, filtres dynamiques

### 5. `domain-entity` — Entité de domaine (Clean Architecture)
- **Pattern** : Entité du domaine séparée du modèle ORM
- **Vu dans** : Madysta `app/domain/entities/`, Baluchon auth-api
- **Fichiers** : `app/domain/entities/{resource}.py`
- **Détails** : Dataclass ou Pydantic BaseModel, logique métier encapsulée, pas de dépendance infra

### 6. `alembic-migration` — Migration Alembic
- **Pattern** : Configuration Alembic + template de migration
- **Vu dans** : Toutes les APIs des 3 projets
- **Fichiers** : `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/xxx.py`
- **Détails** : Connexion DB dans env.py, import des models pour autogenerate, conventions de nommage

### 7. `test-backend-unit` — Tests unitaires backend (pytest)
- **Pattern** : Fixtures pytest, test des use cases, mocking du repository
- **Vu dans** : Baluchon `tests/unit/applications/`, `tests/unit/infrastructure/`
- **Fichiers** : `tests/unit/`, `tests/fixtures/`, `pytest.ini`
- **Détails** : Fixtures database, factory pattern pour créer des entités de test, mocking propre

### 8. `test-backend-integration` — Tests d'intégration backend
- **Pattern** : Tests contre les endpoints avec TestClient
- **Vu dans** : Baluchon `tests/integration/endpoints/`, Madysta `tests/`
- **Fichiers** : `tests/integration/endpoints/test_{resources}.py`, `tests/fixtures/database.py`
- **Détails** : Setup/teardown DB SQLite in-memory, TestClient FastAPI, assertion sur status codes et payloads

---

## 🟡 Priorité MOYENNE — Patterns récurrents dans 2+ projets

### 9. `database-config` — Configuration database (infrastructure)
- **Pattern** : Connection pool, session factory, Base déclarative
- **Vu dans** : Baluchon `shared/config/database.py`, Madysta `infrastructure/database.py`
- **Fichiers** : `app/infrastructure/database.py` ou `shared/database/connection.py`
- **Détails** : `get_db()` dependency, `create_engine()`, `sessionmaker`, env-based config

### 10. `config-settings` — Configuration applicative (pydantic-settings)
- **Pattern** : Settings centralisées avec variables d'environnement
- **Vu dans** : Baluchon `shared/config/settings.py`, Madysta `app/config.py`
- **Fichiers** : `app/config.py` ou `shared/config/settings.py`
- **Détails** : `BaseSettings` Pydantic, `.env` loading, validation des configs, secrets management

### 11. `middleware-auth` — Middleware d'authentification
- **Pattern** : Vérification JWT sur chaque requête entrante
- **Vu dans** : Baluchon `shared/infrastructure/auth_middleware.py`
- **Fichiers** : `shared/infrastructure/auth_middleware.py`
- **Détails** : Extraction du token, vérification signature, injection user_id dans request state

### 12. `middleware-cors-logging` — Middleware CORS + Logging structuré
- **Pattern** : Middleware de logging avec structlog + CORS config
- **Vu dans** : Baluchon `shared/infrastructure/middleware.py`, `shared/infrastructure/logging.py`
- **Fichiers** : `shared/infrastructure/middleware.py`, `shared/infrastructure/logging.py`
- **Détails** : Request/response logging avec timing, correlation ID, structlog JSON formatter

### 13. `rate-limiter` — Rate Limiting
- **Pattern** : Limitation de requêtes par IP/user
- **Vu dans** : Madysta B4F APIs, Baluchon `shared/infrastructure/rate_limiter.py`
- **Fichiers** : `shared/infrastructure/rate_limiter.py`
- **Détails** : Sliding window, configurable limits, bypass pour health checks

### 14. `b4f-proxy-api` — Backend-for-Frontend (proxy API)
- **Pattern** : API proxy qui agrège/transforme les appels vers les backend APIs
- **Vu dans** : Madysta (7 B4F APIs), Baluchon (6 B4F APIs)
- **Fichiers** : `app/presentation/routes/`, `app/infrastructure/middleware/`, `app/config.py`
- **Détails** : httpx client, proxy transparent, transformation de payload, rate limiting, pas de DB propre

### 15. `http-client-service` — Client HTTP partagé
- **Pattern** : Client HTTP réutilisable pour appels inter-services
- **Vu dans** : Baluchon `shared/services/http_client.py`
- **Fichiers** : `shared/services/http_client.py`
- **Détails** : httpx.AsyncClient, retry logic, timeout config, error handling standardisé

### 16. `di-container` — Conteneur d'Injection de Dépendances
- **Pattern** : DI container pour wiring des services
- **Vu dans** : Baluchon `shared/di/container.py`, APIs auth
- **Fichiers** : `shared/di/container.py` ou `app/infrastructure/di/`
- **Détails** : Factory functions, singleton pattern, FastAPI `Depends()` wiring

### 17. `seed-data` — Script de seed (données initiales)
- **Pattern** : Chargement de données de base (mock ou CSV)
- **Vu dans** : Madysta `seed_csv.py`, `seed_mock.py`, Baluchon auth `seed.py`
- **Fichiers** : `app/infrastructure/seed.py` ou `app/infrastructure/seed_mock.py`
- **Détails** : Seed idempotent, superadmin user, données de référence

### 18. `event-bus` — Bus d'événements inter-services
- **Pattern** : Publish/subscribe pour communication asynchrone
- **Vu dans** : Madysta `infrastructure/event_bus.py`, Baluchon shared `event_bus/`
- **Fichiers** : `app/infrastructure/event_bus.py` ou `shared/event_bus/`
- **Détails** : Event dispatcher, event handlers, typed events

---

## 🟢 Priorité BASSE — Patterns spécialisés

### 19. `monitoring-observability` — Monitoring & Observabilité
- **Pattern** : Métriques Prometheus, traces OpenTelemetry
- **Vu dans** : Baluchon `shared/infrastructure/monitoring.py`, `telemetry.py`, `observability.py`
- **Fichiers** : `shared/infrastructure/monitoring.py`, `shared/infrastructure/telemetry.py`
- **Détails** : Prometheus metrics endpoint, request duration histograms, span tracing

### 20. `router-versioned` — Router avec versioning (v1/)
- **Pattern** : Versioning d'API avec préfixe /v1/
- **Vu dans** : Baluchon `app/routes/v1/`
- **Fichiers** : `app/routes/v1/{resources}.py`, `app/routes/__init__.py`
- **Détails** : Sous-router versionné, re-export centralisé

### 21. `shared-library` — Bibliothèque partagée multi-API
- **Pattern** : Package Python partagé entre plusieurs APIs
- **Vu dans** : Baluchon `apis/shared/`, Madysta `apis/shared/`
- **Fichiers** : `shared/pyproject.toml`, `shared/__init__.py`, sous-modules
- **Détails** : Package installable, config/database/infra/di/services partagés

---

## 📊 Résumé

| Priorité | Nombre | Templates |
|----------|--------|-----------|
| 🔴 HAUTE | 8 | api-bootstrap, auth-jwt, use-case, repository-pattern, domain-entity, alembic-migration, test-backend-unit, test-backend-integration |
| 🟡 MOYENNE | 10 | database-config, config-settings, middleware-auth, middleware-cors-logging, rate-limiter, b4f-proxy-api, http-client-service, di-container, seed-data, event-bus |
| 🟢 BASSE | 3 | monitoring-observability, router-versioned, shared-library |
| **Total** | **21** | |
