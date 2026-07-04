# System Design Doc — CDE

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 04 · Technique · **Dernière MAJ** : 2026-07-01
> Le *Design Doc* (façon Google) : l'architecture réelle du système, ses décisions structurantes et leurs compromis. Source normative : [`regles-architecture-deploiement.md` (v1.4)](../regles-architecture-deploiement.md) et [`ARCHITECTURE.md`](../ARCHITECTURE.md). Ce document synthétise et relie ; il ne remplace pas ces références.

## 1. Vue d'ensemble

CDE est un SaaS **multi-tenant** à architecture **micro-services en 3 couches** :

```
Clients ──► Gateway (NGINX Ingress, TLS wildcard, HTTPS only)
                │
   ┌────────────┼─────────────────────────────────────────┐
   │  Frontend (Angular 21, servi par nginx, /)            │
   └────────────┼─────────────────────────────────────────┘
                │  /api/<service>/v1
   ┌────────────▼─────────────────────────────────────────┐
   │  B4F — logique métier (7 API exposées)                │
   │  auth · crm · agent-control · communication ·         │
   │  platform · kb · bob-chat                              │
   └────────────┼─────────────────────────────────────────┘
                │  DNS K8s interne (jamais exposé)
   ┌────────────▼─────────────────────────────────────────┐
   │  Backend — CRUD par entité (14 API internes)          │
   │  user · contact · org · opportunity · activity ·      │
   │  product · email · agent · workflow · kb · usage ·    │
   │  conversation · agent-runtime · agent-memory          │
   └───┬───────────────────────┬───────────────────────────┘
       │ PgBouncer (txn pool)   │ Redis (Event Bus + pub/sub)
   ┌───▼─────────┐         ┌────▼──────────┐
   │ PostgreSQL 16│         │ Milvus (RAG)  │  + externes : Fireworks (LLM),
   └─────────────┘         └───────────────┘    Pipedream, MS Graph, Hunter…
```

## 2. Principes structurants (norme v1.4)

| Principe | Règle | Pourquoi |
|---|---|---|
| **Un seul point d'entrée** | Gateway NGINX unique, HTTPS, TLS wildcard depuis cert-manager | surface d'attaque minimale |
| **Backends invisibles** | aucun backend exposé au gateway ; accès par DNS K8s interne | isolation |
| **B4F pense, Backend range** | logique/agrégation en B4F ; CRUD 1 entité en backend | lisibilité, découplage ([ADR-0001](adr/adr-0001-architecture-deux-tiers-b4f-backend.md)) |
| **Pas de Backend→Backend HTTP** | synchro inter-backend uniquement via Event Bus Redis | pas de monolithe distribué ([ADR-0002](adr/adr-0002-event-bus-redis-inter-backend.md)) |
| **Frontend = une API** | son propre chart Helm, Service ClusterIP, exposé sur `/` | uniformité de déploiement |
| **Clean Architecture** | domain/application/infrastructure/presentation, contrôlé par import-linter | testabilité |

## 3. Couche Frontend

- **Angular 21**, standalone components (aucun NgModule), lazy loading via `loadComponent()`.
- **5 MFE logiques** (`mfe-crm/inbox/bob/platform/settings`) — organisation par dossiers/routing, **pas** de module federation. Compilé en un bundle unique.
- **État** : NGRX (11 feature stores), sans `@ngrx/entity` ni `router-store` (gestion manuelle). Pattern : Composant → dispatch → Effect → Service → HTTP → B4F.
- **Sécurité** : `authGuard` (route), `authInterceptor` (Bearer + refresh 401 + redirect 403), CSP.
- **Servi** par nginx (reverse-proxy vers les 8 B4F, SPA fallback, `/health`). Build multi-stage Docker (node build → nginx).
- Détails : voir le rapport frontend et [Design](../03-design/design-principles.md).

## 4. Couche B4F (7 services exposés)

Chaque B4F : logique métier, agrégation, filtrage, **aucun accès DB ni service externe direct**, appelle les backends via DNS interne. Exemples de valeur ajoutée réelle :
- **crm-b4f** : `/dashboard/summary` compose **en parallèle** (asyncio) 5 backends → totaux + highlights + next_actions.
- **communication-b4f** : `/integrations/overview` agrège connexions + stats labels ; reçoit webhooks ; déclenche workflows.
- **bob-chat-b4f** : orchestration de session, idempotence, appel runtime, gestion des confirmations ; signe `X-Session-Context`.
- **kb-b4f** : `/kb/home` compose catégories + récents + populaires + stats.

Ports (local) : auth 8001, crm 8002, communication 8004, platform 8005, kb 8006, bob-chat 8007, agent-control 8008 (+ bob-cloud-stub 8010).

## 5. Couche Backend (14 services internes)

CRUD pur sur **une entité principale**, possède son schéma et ses migrations Alembic, publie des events. Ports (local) : user 9001, contact 9002, org 9003, opportunity 9004, activity 9005, product 9006, email 9007, agent 9008, workflow 9009, kb 9010, usage 9011, conversation 9012, agent-runtime 9013, agent-memory 9014.

Traits partagés (`apis/shared`) : `TenantMixin`, `AuditMixin`, `SoftDeleteMixin`, client HTTP avec propagation `traceparent`, logging, event bus.

## 6. Données & persistance

- **PostgreSQL 16** via **PgBouncer** (transaction pooling). Contraintes : `pool_pre_ping`, `pool_recycle=300`, pas de prepared statements (`prepare_threshold=None`), noms qualifiés par schéma (pas de `SET search_path`).
- **Un schéma par backend** (`CREATE SCHEMA <service>`), migrations Alembic avec **downgrade symétrique testé en CI**.
- **Migrations en prod** : initContainer + **Lease Kubernetes** (évite les migrations concurrentes multi-pods, sans dépendre de Redis).
- Détails : [Data Model](data-model.md).

## 7. Bus d'événements

- **Redis** partagé, canal `{source-api}.{entity}.{action}` (ex. `contact-backend-api.contact.created`).
- Contrat : `{event, timestamp, tenant_id, trace_id, data}`. Fire-and-forget, cohérence éventuelle, subscribers idempotents. B4F ne publie ni ne souscrit. Voir [ADR-0002](adr/adr-0002-event-bus-redis-inter-backend.md).

## 8. Sous-système agentique (Bob)

Chaîne : `bob-chat-b4f` (session, orchestration) → `agent-runtime-backend` (provider LLM, tool-loop, confirmations, gouvernance) → `agent-memory-backend` (RAG/Milvus) + `conversation-backend` (messages) + `agent-control-b4f` (BCC/training/gouvernance admin). Providers : **Fireworks** (`kimi-k2p7-code`) + fallback **local déterministe**. Détails complets : [Runtime agentique](agentic-runtime-design.md).

## 9. Intégrations externes

| Service | Usage | Où |
|---|---|---|
| **Fireworks** | LLM runtime + embeddings (`qwen3-embedding-8b`, 4096d) | agent-runtime, agent-memory |
| **Pipedream** | email (send/reply/forward/sync), connecteurs MCP | email-backend, communication-b4f |
| **Microsoft 365 / Graph** | email legacy, OAuth, webhooks | email-backend |
| **Milvus** | vecteurs RAG (optionnel en local) | agent-memory |
| **Hunter / Bright Data / Serper** | enrichissement contacts/orgs | backends CRM |

Règle : **les services externes sont appelés depuis les backends**, jamais depuis les B4F.

## 10. Sécurité (résumé)

Multi-tenant par `tenant_id` (immuable, dans le JWT), RBAC (`Permission`/`Role`/`UserRole`), JWT HS256 (access 24 h / refresh 7 j), backends non exposés, secrets hors repo, HTTPS + TLS wildcard, signature de contexte de session B4F→runtime. Analyse complète : [Threat Model](threat-model.md).

## 11. Déploiement & CI/CD

- **CI/CD GitLab** parent/child (template `ci-cd-unified-template v1.0.70`) : `discover` → child `test → build → verify → deploy → smoke-test` (+ rollback manuel).
- **Build** Kaniko → Harbor (tag SHA, jamais `latest`), **verify** (scan Trivy + signature Cosign), **deploy** Helm (dev auto, staging/prod manuel), **smoke-test** post-deploy.
- **Charts** : `api-chart`, `frontend-chart`, `gateway-chart` (repo partagé).
- Local : `docker-compose` (postgres, pgbouncer, redis, alloy + 22 services) ; scripts `run_all_apis*.sh`, `migrate_all_apis.sh`.

## 12. Observabilité

Probes `/liveness /readiness /startup /health /metrics` sur chaque API ; logs JSON (structlog) avec contextvars (`trace_id/request_id/tenant_id/user_id`) ; traces OTel → Alloy (OTLP). Détails & SLO : [SLO & Observabilité](slo-observability.md).

## 13. Compromis & risques d'architecture

| Choix | Bénéfice | Coût / risque |
|---|---|---|
| 22 micro-services | découplage, déploiement indépendant, respect v1.4 | **complexité opérationnelle** élevée pour une petite équipe |
| Relations N:N en JSON (activités) | simplicité | non requêtable en SQL, cohérence applicative |
| MFE logiques (pas module federation) | simplicité de build | pas de déploiement frontend indépendant par domaine |
| Runtime agentique maison | contrôle total (gating, routage, gouvernance) | charge de maintenance ([ADR-0004](adr/adr-0004-runtime-agentique-maison-vs-langgraph.md)) |
| Dépendances externes (Fireworks, Pipedream) | time-to-market | coût, rate-limits, rupture d'API ([Risk Register](../06-gouvernance/risk-register.md)) |

## 14. Questions ouvertes techniques
- Scalabilité du tool-loop à N utilisateurs concurrents (coût/latence).
- Stratégie de rename des tables `membrane_*`.
- Consolidation KB relationnelle vs `KnowledgeCollection` vectorielle.
- Faut-il un `@ngrx/entity` à mesure que les collections grossissent ?

Voir les [ADRs](adr/) pour les décisions déjà tranchées.
