# Template: Docker Compose Multi-Services

> Recette pour orchestrer tous les services (APIs + frontend + DB + monitoring).

## Fichier à créer

`docker-compose.yml`

```yaml
version: '3.8'

services:
  # ═══════════════════════════════════════
  # DATABASE
  # ═══════════════════════════════════════
  database:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER:-admin}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-admin123}
      POSTGRES_DB: ${DB_NAME:-app}
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-admin}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ═══════════════════════════════════════
  # BACKEND APIs
  # ═══════════════════════════════════════
  auth-api:
    build:
      context: ./apis/auth-api
    restart: unless-stopped
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=postgresql://${DB_USER:-admin}:${DB_PASSWORD:-admin123}@database:5432/${DB_NAME:-app}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-only-secret-not-for-production}
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - PORT=8001
    depends_on:
      database:
        condition: service_healthy

  # {resource}-backend-api:
  #   build:
  #     context: ./apis/{resource}-backend-api
  #   restart: unless-stopped
  #   ports:
  #     - "8002:8002"
  #   environment:
  #     - DATABASE_URL=postgresql://${DB_USER:-admin}:${DB_PASSWORD:-admin123}@database:5432/${DB_NAME:-app}
  #     - JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-only-secret-not-for-production}
  #     - ENVIRONMENT=${ENVIRONMENT:-development}
  #     - PORT=8002
  #   depends_on:
  #     database:
  #       condition: service_healthy

  # ═══════════════════════════════════════
  # FRONTEND
  # ═══════════════════════════════════════
  frontend:
    build:
      context: ./frontend
    restart: unless-stopped
    ports:
      - "4200:80"
    depends_on:
      - auth-api

  # ═══════════════════════════════════════
  # OBSERVABILITY (optionnel)
  # ═══════════════════════════════════════
  # jaeger:
  #   image: jaegertracing/all-in-one:latest
  #   ports:
  #     - "16686:16686"  # UI
  #     - "4317:4317"    # OTLP gRPC

volumes:
  postgres_data:
```

## `.env` template

```env
# Database
DB_USER=admin
DB_PASSWORD=admin123
DB_NAME=app
DB_PORT=5432

# JWT
JWT_SECRET_KEY=dev-only-secret-not-for-production

# Environment
ENVIRONMENT=development
```

## Règles NON-NÉGOCIABLES

1. PostgreSQL avec healthcheck obligatoire
2. `depends_on` avec `service_healthy`
3. Secrets via variables d'environnement — jamais hardcodés
4. Volumes nommés pour la persistance
5. Ports exposés par service : auth=8001, backend=8002+, frontend=4200
