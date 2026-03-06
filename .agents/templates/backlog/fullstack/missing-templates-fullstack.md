# 🔗 Backlog — Templates Full-Stack Manquants

> Patterns transversaux identifiés dans **ASQ-CRM**, **Madysta ERP**, **Le Baluchon** qui n'ont PAS de template HDQ.
> Chaque entrée = 1 template à créer dans `templates/code/fullstack/`.

---

## 🔴 Priorité HAUTE — Bloquants pour tout nouveau projet

### 1. `project-bootstrap` — Bootstrap complet d'un nouveau projet
- **Pattern** : Structure de base d'un projet full-stack multi-API + frontend Angular
- **Vu dans** : Structure identique dans Madysta et Baluchon
- **Fichiers** :
  ```
  project-root/
  ├── apis/
  │   ├── shared/              ← lib partagée
  │   ├── auth-api/            ← première API
  │   └── {resource}-backend-api/
  ├── frontend/
  │   └── src/app/
  │       ├── core/            ← guards, interceptors, services, models
  │       ├── features/        ← modules fonctionnels
  │       ├── layout/          ← main-layout, auth-layout, sidebar, header
  │       ├── shared/          ← components, directives, pipes
  │       └── store/           ← NgRx stores
  ├── deploy/
  │   ├── helm/
  │   └── observability/
  ├── docker-compose.yml
  ├── .gitlab-ci.yml
  ├── run_all_apis.sh
  ├── run_frontend.sh
  └── README.md
  ```
- **Détails** : Initialisation complète incluant .gitignore, .env.sample, scripts de run, proxy config

### 2. `auth-module-fullstack` — Module d'authentification complet
- **Pattern** : Auth backend (API) + frontend (login page, guards, interceptor, service, store)
- **Vu dans** : Les 3 projets
- **Séquence** :
  1. Backend: `auth-api` avec JWT + bcrypt
  2. Frontend: `page-login` + `service-auth` + `auth-guard` + `guest-guard` + `interceptor-auth` + `store/auth`
  3. Config: CORS, httpOnly cookies
- **Détails** : Orchestre 6+ templates individuels dans un ordre strict

### 3. `crud-module-clean-arch` — Module CRUD Clean Architecture
- **Pattern** : Module CRUD avec Clean Architecture complète (pas le simple CRUD existant)
- **Vu dans** : Madysta opportunities, Baluchon clients
- **Séquence** :
  1. Backend: domain entity → repository → use case → schemas → routes → migration → tests
  2. Frontend: model → service → store → page-list → page-detail → form
- **Détails** : Extension du `crud-module` existant avec les couches Clean Architecture ajoutées

---

## 🟡 Priorité MOYENNE — Patterns multi-projets

### 4. `b4f-module` — Module Backend-for-Frontend complet
- **Pattern** : API B4F + service frontend dédié + store
- **Vu dans** : Madysta (7 B4F APIs), Baluchon (6 B4F APIs)
- **Séquence** :
  1. Backend B4F: `b4f-proxy-api` (routes, schemas, no DB)
  2. Frontend: `service-http` pointant vers le B4F + `store-feature-ngrx`
- **Détails** : Pattern d'agrégation où le B4F combine les données de plusieurs backend APIs

### 5. `docker-compose-stack` — Stack Docker Compose
- **Pattern** : docker-compose.yml complet pour une stack multi-API + frontend + DB
- **Vu dans** : Madysta, Baluchon
- **Fichiers** : `docker-compose.yml`, `Dockerfile` (par service)
- **Détails** : Networks, volumes, env files, depends_on, health checks, port mapping

### 6. `ci-cd-gitlab` — Pipeline CI/CD GitLab
- **Pattern** : `.gitlab-ci.yml` complet avec stages build/test/deploy
- **Vu dans** : Madysta (101KB!), Baluchon (78KB)
- **Fichiers** : `.gitlab-ci.yml`
- **Détails** : Stages (lint, test, build, deploy), jobs par API, cache, artifacts, environments (dev/staging/prod)

### 7. `helm-deploy` — Charts Helm pour déploiement K8s
- **Pattern** : Charts Helm pour API, frontend, gateway, DB, Redis
- **Vu dans** : Madysta `deploy/helm/`
- **Fichiers** :
  ```
  deploy/helm/
  ├── api-chart/           ← deployment, service, hpa, pdb, configmap, secret
  ├── frontend-chart/      ← deployment, service, hpa, pdb
  ├── gateway-chart/       ← ingress, nginx configmap
  ├── postgresql-chart/    ← deployment, pvc, service
  ├── redis-chart/         ← deployment, pvc, service, configmap
  └── database-backup-chart/
  ```
- **Détails** : Templates Helm avec `_helpers.tpl`, values par environnement

### 8. `observability-stack` — Stack d'observabilité
- **Pattern** : Configuration Prometheus + Grafana + Loki + Tempo + Alloy
- **Vu dans** : Madysta `deploy/observability/`, Baluchon `deploy/observability/`
- **Fichiers** : `prometheus-config.yml`, `loki-config.yaml`, `tempo-config.yaml`, `promtail-config.yaml`, `alloy-config.alloy`
- **Détails** : Collecte de métriques, logs centralisés, traces distribuées

### 9. `e2e-tests-playwright` — Tests E2E avec Playwright
- **Pattern** : Tests end-to-end du frontend avec Playwright
- **Vu dans** : Madysta `frontend/e2e/`
- **Fichiers** : `frontend/e2e/`, `frontend/playwright.config.ts`
- **Détails** : Config Playwright, spec patterns, page objects, CI integration

### 10. `run-scripts` — Scripts de run pour développement local
- **Pattern** : Scripts bash pour démarrer/tester toutes les APIs et le frontend
- **Vu dans** : Madysta, Baluchon
- **Fichiers** : `run_all_apis.sh`, `run_frontend.sh`, `run_all_apis_tests.sh`, `migrate_all_apis.sh`
- **Détails** : Détection des APIs, migrations auto, parallel start, colored output

---

## 🟢 Priorité BASSE — Patterns spécialisés

### 11. `pre-commit-hooks` — Configuration pre-commit
- **Pattern** : Hooks de validation avant commit
- **Vu dans** : Madysta `.pre-commit-config.yaml`
- **Fichiers** : `.pre-commit-config.yaml`
- **Détails** : ruff, mypy, eslint, prettier, trailing whitespace

### 12. `proxy-config` — Configuration proxy Angular
- **Pattern** : Proxy de développement Angular → APIs backend
- **Vu dans** : Madysta `frontend/proxy.conf.json`, `proxy.docker.conf.json`
- **Fichiers** : `frontend/proxy.conf.json`, `frontend/proxy.docker.conf.json`
- **Détails** : Mapping par API, changement d'origin, secure: false pour dev

### 13. `nginx-config` — Configuration Nginx frontend
- **Pattern** : Fichier nginx.conf pour servir le frontend en production
- **Vu dans** : Madysta, Baluchon, ASQ-CRM
- **Fichiers** : `frontend/nginx.conf`, `frontend/entrypoint.sh`
- **Détails** : SPA fallback, compression gzip, headers cache, proxy_pass vers APIs

### 14. `deploy-scripts` — Scripts de déploiement
- **Pattern** : Scripts Helm deploy pour chaque composant
- **Vu dans** : Madysta `deploy/scripts/`, Baluchon `deploy/scripts/`
- **Fichiers** : `deploy/scripts/deploy-api.sh`, `deploy/scripts/deploy-frontend.sh`, etc.
- **Détails** : Helm upgrade/install, namespace management, secret injection

---

## 📊 Résumé

| Priorité | Nombre | Templates |
|----------|--------|-----------|
| 🔴 HAUTE | 3 | project-bootstrap, auth-module-fullstack, crud-module-clean-arch |
| 🟡 MOYENNE | 7 | b4f-module, docker-compose-stack, ci-cd-gitlab, helm-deploy, observability-stack, e2e-tests-playwright, run-scripts |
| 🟢 BASSE | 4 | pre-commit-hooks, proxy-config, nginx-config, deploy-scripts |
| **Total** | **14** | |

---

## 📈 Vue d'ensemble globale (tous layers)

| Layer | Templates existants | Templates manquants | Couverture |
|-------|--------------------|--------------------|------------|
| Backend | 3 | 21 | **12.5%** |
| Frontend | 6 (+1 badge, +1 dialog) | 29 | **22%** |
| Full-Stack | 1 | 14 | **6.7%** |
| **Total** | **10** | **64** | **13.5%** |

> ⚠️ Pour atteindre **100% de couverture**, il faut créer **64 templates** supplémentaires.
