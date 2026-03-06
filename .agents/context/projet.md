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
| **Frontend** | Angular 20+ (standalone components, native CSS) |
| **Backend APIs** | FastAPI + Python 3.11+ |
| **Agent Orchestration** | LangGraph |
| **LLM principal** | Groq (Llama 3.3 70B, Whisper) |
| **LLM fallback** | OpenRouter (Claude, GPT — quand nécessaire) |
| **Base de données** | PostgreSQL + pgvector (embeddings) + Apache AGE (graph) |
| **Auth** | JWT centralisé |
| **Search / Scraping** | Serper.dev + Groq LLM extraction |
| **Async / Queue** | Redis + Celery |
| **Logging** | Structlog JSON |
| **Conteneurisation** | Docker + Docker Compose |
| **CI/CD** | GitLab CI/CD |

## 3. Architecture

```
   🎙️ Voice / ✏️ Chat (Angular 20+)
            │
            ▼
   [Groq Whisper] ─── transcription (si voice)
            │
            ▼
   [Intent Parser] ─── Groq LLM → action + paramètres
            │
            ▼
   [LangGraph Orchestrator] ─── graphs d'état, parallélisme, checkpointing
            │
   ┌────────┼────────────────────────────┐
   │        │                            │
   ▼        ▼                            ▼
[Search]  [Scraper]  [Email]  [RAG]   [Drive]   ← Agents spécialisés
 Serper    Groq      IMAP/    pgvec   GDrive
 .dev               Gmail     tor    OneDrive
                    Outlook          Box / S3
            │
            ▼
   [PostgreSQL + pgvector + Apache AGE]
     Relations   Embeddings   Graph
     tenant_id   RAG search   Cartographie
```

### Services

| Service | Rôle | Intégrations |
|---|---|---|
| **BFF** | Backend-for-Frontend | — |
| **Auth** | JWT + tenant isolation | — |
| **AI Orchestrator** | LangGraph agent chains | Groq, OpenRouter |
| **Connectors** | Ingestion données externes | Serper, Email, Drive, Whisper |

## 4. Intégrations externes

| Service | Usage | Variable |
|---|---|---|
| Groq | LLM principal + Whisper voice | GROQ_API_KEY |
| OpenRouter | LLM premium (fallback) | OPENROUTER_API_KEY |
| Serper.dev | Web search API | SERPER_API_KEY |
| Gmail / Outlook | Email IMAP/SMTP + API | EMAIL_* |
| Google Drive | Ingestion fichiers clients | GDRIVE_* |
| OneDrive / Box / S3 | Ingestion fichiers alternatifs | STORAGE_* |

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
