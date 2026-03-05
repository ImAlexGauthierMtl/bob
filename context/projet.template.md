---
name: "Ω:CONTEXT:[NOM DU PROJET]"
version: 1.0.0
updated: "[DATE_ISO]"
---

# Ω:CONTEXT:[NOM DU PROJET] — Root

> Ce fichier est la racine du HDQ pour ce projet.
> Il doit être lu au début de chaque session de collaboration.

---

## 1. Identité du projet

- **Nom** : [Nom du projet]
- **Domaine** : [Hôtellerie / CRM / ERP / SaaS / ...]
- **Type** : [Monorepo / Micro-services / BFF / Simple API]
- **Client** : [Nom du client]
- **Équipe technique** : The Smart Crew

## 2. Stack technique

| Couche | Technologies |
|---|---|
| **Backend APIs** | [FastAPI + Python 3.11+ / ...] |
| **Frontend** | [Angular 20+ / ...] |
| **Base de données** | [PostgreSQL / SQLite / ...] |
| **Auth** | [JWT centralisé / ...] |
| **Logging** | [Structlog JSON / ...] |
| **Conteneurisation** | [Docker + Docker Compose] |
| **Orchestration** | [Kubernetes / Docker seul] |
| **CI/CD** | [GitLab CI/CD / GitHub Actions / ...] |

## 3. Architecture

<!-- Décrire le pattern architectural avec un diagramme ASCII -->

```
Frontend
    │
    ▼
[API Layer]       ← Décrire les couches
    │
    ▼
[Database]
```

### APIs actives

| API | Port | Rôle | Intégration externe |
|---|---|---|---|
| [api-name] | [port] | [rôle] | [service externe ou —] |

## 4. Intégrations externes

| Service | Usage | Variable |
|---|---|---|
| [Nom] | [Description] | [ENV_VAR] |

## 5. Environnements

| Environnement | URL | Déclencheur |
|---|---|---|
| **Dev** | [url] | [Merge sur develop / ...] |
| **Staging** | [url] | [Manuel / ...] |
| **Prod** | [url] | [Tag / ...] |

## 6. Conventions

- **Commits** : `[service] type: description`
- **Branches** : `main` (prod), `develop` (intégration), `feature/*`, `fix/*`
- **Backend** : snake_case, type hints obligatoires, 100% test coverage
- **Secrets** : Jamais dans le code
