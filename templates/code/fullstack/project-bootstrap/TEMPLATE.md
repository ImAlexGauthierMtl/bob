# Template: Project Bootstrap — Structure complète

> Orchestrateur : crée la structure de base d'un projet full-stack multi-API.

## Structure à créer

```
{project-name}/
├── apis/
│   ├── shared/                          → voir shared-library/
│   │   ├── __init__.py
│   │   ├── config/settings.py           → voir config-settings/
│   │   ├── database/connection.py       → voir database-config/
│   │   ├── infrastructure/
│   │   │   ├── logging.py               → voir middleware-cors-logging/
│   │   │   ├── middleware.py            → voir middleware-cors-logging/
│   │   │   ├── auth_middleware.py       → voir middleware-auth/
│   │   │   ├── monitoring.py            → voir monitoring-observability/
│   │   │   └── rate_limiter.py          → voir rate-limiter/
│   │   └── services/http_client.py      → voir http-client-service/
│   └── auth-api/                        → voir auth-jwt/ + api-bootstrap/
├── frontend/
│   ├── src/app/
│   │   ├── core/
│   │   │   ├── guards/                  → voir auth-guard/ + guest-guard/
│   │   │   ├── interceptors/            → voir interceptor-auth/ + interceptor-snake-case/
│   │   │   ├── services/               → voir service-auth/ + service-cookie/
│   │   │   ├── models/                  → voir model-api/
│   │   │   └── pipes/                   → voir pipe-sanitize/
│   │   ├── features/dashboard/          → voir page-dashboard/
│   │   ├── layout/                      → voir layout-main/
│   │   ├── shared/
│   │   │   ├── components/              → voir component-*/
│   │   │   └── directives/              → voir directive-file-drop/
│   │   └── store/auth/                  → voir store-feature-ngrx/
│   ├── proxy.conf.json                  → voir environment-config/
│   └── angular.json
├── deploy/
│   ├── helm/                            → voir helm-deploy/
│   └── observability/                   → voir observability-stack/
├── docker-compose.yml                   → voir docker-compose-multi/
├── .gitlab-ci.yml                       → voir ci-cd-gitlab/
├── run_all_apis.sh                      → voir run-scripts/
├── run_frontend.sh                      → voir run-scripts/
├── .env.sample
├── .gitignore
└── README.md
```

## `.env.sample`

```env
# Database
DATABASE_URL=postgresql://admin:admin123@localhost:5432/{project_name}

# JWT
JWT_SECRET_KEY=change-me-in-production

# Environment
ENVIRONMENT=development
```

## `.gitignore`

```
__pycache__/
*.pyc
.env
*.egg-info/
node_modules/
dist/
.angular/
venv/
```

## Séquence d'initialisation

1. Créer la structure de dossiers
2. Initialiser `shared/` (config, database, middleware, logging)
3. Créer `auth-api/` (templates: `api-bootstrap` + `auth-jwt`)
4. `ng new frontend --standalone --routing --style=scss`
5. Configurer frontend (guards, interceptors, services, store, layouts)
6. Créer `docker-compose.yml`
7. Ajouter scripts `run_*.sh`
8. Premier commit
