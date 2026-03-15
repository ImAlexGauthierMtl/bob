# Deployment Guide - Croo Digital Experience v2.0

## Architecture

The CI/CD pipeline deploys to Kubernetes using Helm charts via GitLab CI/CD.

### Pipeline Stages

1. **.pre** — Generate dynamic API jobs (test, build, deploy, smoke-test)
2. **test** — Run unit tests (Python APIs + Angular frontend)
3. **build** — Build Docker images and push to GitLab Container Registry
4. **deploy-dev** — Deploy to dev environment via Helm + run database migrations
5. **smoke-test-dev** — Verify all services are healthy
6. **rollback-dev** — Manual rollback (one click)

### Branching Strategy

- Push to `develop` → auto-deploy to **dev**
- Push to `main` → auto-deploy to **staging** (when configured)
- Git tag → manual deploy to **prod** (when configured)

## Services

| Service | Port | Type | Exposed via Gateway |
|---------|------|------|---------------------|
| frontend | 4700 | Angular/nginx | Yes (/) |
| b4f-api | 8000 | BFF Gateway | Yes (/api/v1/bff) |
| auth-api | 8001 | Backend | Yes (/api/v1/auth) |
| crm-backend-api | 8002 | Backend | No (internal) |
| ai-agent-api | 8003 | Backend | No (internal) |
| communication-api | 8004 | Backend | No (internal) |
| platform-services-api | 8005 | Backend | No (internal) |
| kb-api | 8006 | Backend | No (internal) |
| auth-b4f-api | 8011 | BFF | Yes (/api/v1/auth-bff) |
| crm-b4f-api | 8012 | BFF | Yes (/api/v1/crm-bff) |
| ai-agent-b4f-api | 8013 | BFF | Yes (/api/v1/ai-agent-bff) |
| communication-b4f-api | 8014 | BFF | Yes (/api/v1/communication-bff) |
| platform-b4f-api | 8015 | BFF | Yes (/api/v1/platform-bff) |
| kb-b4f-api | 8016 | BFF | Yes (/api/v1/kb-bff) |

## GitLab CI/CD Variables

Configure these in **GitLab > Settings > CI/CD > Variables**:

### Required (Dev)

| Variable | Description | Example |
|----------|-------------|---------|
| `DEV_KUBECONFIG` | Kubeconfig file, base64 encoded | `cat ~/.kube/config \| base64` |
| `DEV_DATABASE_HOST` | PostgreSQL host | `postgres.example.com` |
| `DEV_DATABASE_PORT` | PostgreSQL port | `5432` |
| `DEV_DATABASE_NAME` | Database name | `croo_digital_experience` |
| `DEV_DATABASE_USER` | Database user | `croo` |
| `DEV_DATABASE_PASSWORD` | Database password | (masked) |
| `JWT_SECRET_KEY` | JWT signing key (shared by auth-api and BFF APIs) | (masked) |

### Optional (Dev)

| Variable | Description | Default |
|----------|-------------|---------|
| `DEV_ADMIN_USERNAME` | Admin email for initial setup | `admin@croo.digital` |
| `DEV_ADMIN_PASSWORD` | Admin password for initial setup | (none, skips provisioning) |
| `GROQ_API_KEY` | Groq API key for AI agent | (none) |
| `MS365_CLIENT_ID` | Microsoft 365 client ID | (none) |
| `MS365_CLIENT_SECRET` | Microsoft 365 client secret | (none) |
| `MS365_TENANT_ID` | Microsoft 365 tenant ID | (none) |

## Environments

### Dev
- **Namespace:** `cde-dev`
- **URL:** https://app-cde-dev-01.dev.thesmartcrew.com
- **Trigger:** Push to `develop` branch

### Staging (future)
- **Namespace:** `cde-staging`
- **URL:** https://app-cde-dev-01.staging.thesmartcrew.com
- **Trigger:** Push to `main` branch

### Prod (future)
- **Namespace:** `cde-prod`
- **Trigger:** Git tag (manual deploy)

## Helm Charts

- `deploy/helm/api-chart/` — Generic chart for all FastAPI microservices
- `deploy/helm/frontend-chart/` — Chart for Angular frontend (nginx)
- `deploy/helm/gateway-chart/` — Chart for Nginx Ingress (API routing)
- `deploy/helm/values/{env}/` — Environment-specific values

## Deploy Scripts

- `deploy/scripts/discover-apis.sh` — Auto-discover APIs from `apis/` directory
- `deploy/scripts/deploy-api.sh` — Deploy a single API via Helm
- `deploy/scripts/deploy-frontend.sh` — Deploy frontend via Helm
- `deploy/scripts/create-gateway.sh` — Create/update the Ingress gateway
- `deploy/scripts/get-api-port.sh` — Resolve API port from docker-compose or fallback
- `deploy/scripts/get-api-route-prefix.sh` — Resolve gateway route prefix
- `deploy/scripts/get-namespace.sh` — Map environment to Kubernetes namespace

## Directory Naming Convention

APIs in the repository use `~` in folder names for B4F APIs (e.g., `apis/auth~b4f-api/`).
In Kubernetes, `~` is replaced by `-` (e.g., `auth-b4f-api`). The pipeline handles this
conversion automatically in build and deploy scripts.
