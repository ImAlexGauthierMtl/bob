---
name: dx_intermediate_create_local_dev
description: Crée l'environnement de développement local conforme — scripts wrappers racine (run_all_apis.sh, etc.), docker-compose.yml avec postgres+pgbouncer transaction mode+redis+alloy, .env.example documenté, conventions de nommage par préfixe. À invoquer pendant le bootstrap d'un projet pour qu'un dev puisse cloner et lancer immédiatement.
metadata:
  reference: § 11 de docs/architecture/regles-architecture-deploiement.md
---

# dx_intermediate_create_local_dev

## Paramètres

- Liste des APIs (pour les préfixes et ports)
- Frontend présent ?

## Workflow

### 1. Scripts wrappers racine

À créer (cf. § 11.1) :

| Script | Contenu |
|---|---|
| `run_all_apis.sh` | Découvre `apis/exposed/*-b4f-api/` + `apis/internal/*-backend-api/`, lance chaque `run_api.sh` en arrière-plan. Supporte `--stop`, `--restart`, et un filtre par nom |
| `migrate_all_apis.sh` | Découvre tous les Backend, exécute leur `migrate.sh` |
| `run_all_apis_tests.sh` | Découvre toutes les APIs, exécute `run_tests.sh`, agrège la coverage |
| `run_frontend.sh` | `ng serve` (si frontend présent) |
| `run_frontend_tests.sh` | `ng test --coverage` |
| `run_frontend_e2e.sh` | `cd frontend && npx playwright test` |

**Aucune logique métier dans ces scripts** — pure orchestration.

Exit code 0 si tout passe, non-zéro sinon. Logs préfixés par nom d'API.

### 2. docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USERNAME}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_DATABASE}
    volumes:
      - pg_data:/var/lib/postgresql/data

  pgbouncer:
    image: edoburu/pgbouncer
    environment:
      DB_HOST: postgres
      DB_USER: ${DB_USERNAME}
      DB_PASSWORD: ${DB_PASSWORD}
      POOL_MODE: transaction      # § 2.7.4 obligatoire
      MAX_CLIENT_CONN: 200
    depends_on: [postgres]

  redis:
    image: redis:7-alpine
    # Sert au bus d'événements ET aux locks de migration (§ 2.4 + § 2.7.5)

  alloy:
    image: grafana/alloy
    # Collecteur OTLP local — toutes les APIs envoient vers http://alloy:4317

volumes:
  pg_data:
```

### 3. .env.example

```env
# Variables globales — mêmes noms que les variables CI/CD K8s
DB_HOST=pgbouncer
DB_USERNAME=app_user
DB_PASSWORD=devpassword
DB_DATABASE=app
DATABASE_SSLMODE=disable

REDIS_URL=redis://redis:6379/0

OTEL_EXPORTER_OTLP_ENDPOINT=http://alloy:4317

# Variables par API — préfixe = nom de dossier en SNAKE_CASE
# Bannissement : pas de AUTHENTICATION_*

AUTH_B4F_API_PORT=8001
AUTH_B4F_API_LOG_LEVEL=DEBUG

IAM_BACKEND_API_PORT=9001
IAM_BACKEND_API_LOG_LEVEL=DEBUG

# ... une section par API
```

### 4. .gitignore

Vérifier que `.env` est dans `.gitignore` (pas `.env.example`).

## Base skills

- `dx_base_create_local_root_wrappers`
- `dx_base_create_local_compose`
- `dx_base_create_local_env_example`

## Anti-patterns

1. Hardcoder un port dans `docker-compose.yml` ou dans `run_api.sh`
2. PgBouncer en `pool_mode = session` (incompatible avec § 2.7.4)
3. Omettre `redis` ou `alloy` du compose (§ 11.3 services obligatoires)
4. Mettre des secrets de prod dans `.env.example`
5. Mettre de la logique métier dans `run_all_apis.sh`
6. Réintroduire `AUTHENTICATION_*` (banni)
