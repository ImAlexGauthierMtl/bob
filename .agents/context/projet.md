---
name: "Ω:CONTEXT:Croo Digital Experience"
version: 1.0.0
updated: "2026-03-05"
---

# Ω:CONTEXT:Croo Digital Experience — Root

> Ce fichier est la racine du HDQ pour ce projet.
> Il doit être lu au début de chaque session de collaboration.

---

## 1. Identité du projet

- **Nom** : Croo Digital Experience
- **Domaine** : CRM/ERP AI-first — Expérience numérique unifiée
- **Type** : Monorepo — Micro-services + BFF
- **Client** : Croo (The Smart Crew)
- **Équipe technique** : The Smart Crew
- **Vision** : Réinventer l'expérience CRM/ERP avec l'IA au centre des workflows et des contrôles. Moins de fonctions codées, moins d'interface, plus de relation humain-IA. Une seule app pour gérer emails, meetings, collaboration, etc.

## 2. Stack technique

| Couche | Technologies |
|---|---|
| **Backend APIs** | FastAPI + Python 3.11+ |
| **Frontend** | Angular 20+ |
| **Base de données** | PostgreSQL |
| **Auth** | JWT centralisé |
| **Logging** | Structlog JSON |
| **Conteneurisation** | Docker + Docker Compose |
| **CI/CD** | GitLab CI/CD |

## 3. Architecture

```
Frontend (Angular 20+)
    │
    ▼
[BFF Layer]  ← Backend-for-Frontend
    │
    ├──▶ [Auth Service]
    ├──▶ [Core CRM Service]
    ├──▶ [AI Orchestrator]  ← OpenRouter / Groq / Alibaba
    └──▶ [Integration Service]  ← Zoho, Stripe, Email, Calendar
              │
              ▼
         [PostgreSQL]
```

### APIs actives

| API | Port | Rôle | Intégration externe |
|---|---|---|---|
| bff | TBD | Backend-for-Frontend | — |
| auth | TBD | Authentification JWT | — |
| ai-orchestrator | TBD | Orchestration IA | OpenRouter, Groq, Alibaba |
| integrations | TBD | Connecteurs externes | Zoho, Stripe, Email, Calendar |

## 4. Intégrations externes

| Service | Usage | Variable |
|---|---|---|
| OpenRouter | LLM routing multi-provider | OPENROUTER_API_KEY |
| Groq | Inférence LLM rapide | GROQ_API_KEY |
| Alibaba | IA / Cloud services | ALIBABA_API_KEY |
| Zoho | CRM, Desk, Mail | ZOHO_* |
| Stripe | Paiements | STRIPE_* |

## 5. Environnements

| Environnement | URL | Déclencheur |
|---|---|---|
| **Dev** | localhost | Manuel |
| **Staging** | TBD | Merge sur develop |
| **Prod** | TBD | Tag sur main |

## 6. Conventions

- **Commits** : `[service] type: description`
- **Branches** : `main` (prod), `develop` (intégration), `feature/*`, `fix/*`
- **Backend** : snake_case, type hints obligatoires, 100% test coverage
- **Frontend** : kebab-case fichiers, pas de `any`, strict mode
- **Secrets** : Jamais dans le code

## 7. Design DNA

| Propriété | Valeur |
|---|---|
| **Palette** | Noir `#000` + Blanc `#FFF` + Accent `#FF4500` |
| **Typographie** | Inter (200-700) |
| **Style** | Minimaliste, angles droits (pas de rounded), espaces généreux |
| **Icônes** | Font Awesome 6 |
| **Principe** | Épuré, premium, AI-in-the-loop visible |
