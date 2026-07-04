# PRD / Cahier des charges — Croo Digital Experience

> **Statut** : Draft v1.0 · **DRI** : Alexandre Gauthier · **Couche** : 02 · Produit · **Dernière MAJ** : 2026-07-01
> Ce document est le **cahier des charges** de CDE : ce que le produit doit faire, pour qui, avec quelles exigences fonctionnelles et non-fonctionnelles. Il combine le format *PRD* (Google/Meta) et le *cahier des charges* francophone. Il est **descriptif de l'existant** (le code) autant que **prescriptif** (les exigences à tenir).

## Table des matières
1. [Contexte & objectifs](#1-contexte--objectifs)
2. [Périmètre](#2-périmètre)
3. [Utilisateurs & rôles](#3-utilisateurs--rôles)
4. [Exigences fonctionnelles par domaine](#4-exigences-fonctionnelles-par-domaine)
5. [Exigences transverses](#5-exigences-transverses)
6. [Exigences non-fonctionnelles](#6-exigences-non-fonctionnelles-enf)
7. [Contraintes & hypothèses](#7-contraintes--hypothèses)
8. [Critères d'acceptation & métriques](#8-critères-dacceptation--métriques)
9. [Hors périmètre & questions ouvertes](#9-hors-périmètre--questions-ouvertes)

---

## 1. Contexte & objectifs

**Contexte** : voir [Vision Produit](../00-vision/product-vision.md) et [PR/FAQ](../01-discovery/prfaq.md). CDE est un espace de travail commercial B2B multi-tenant où un copilote IA (« Bob ») exécute le travail de suivi sous contrôle humain.

**Objectifs produit (ce PRD sert à…)** :
- **O1** — Réduire le temps de saisie/administration CRM à quasi zéro (saisie par Bob + enrichissement auto).
- **O2** — Unifier email et CRM (contexte au même endroit, liaison automatique).
- **O3** — Permettre la délégation de tâches à un agent **de façon sûre** (confirmation, traçabilité, gouvernance).
- **O4** — Donner aux managers une visibilité fiable (pipeline, analytics, usage/coût).
- **O5** — Tenir des garanties de sécurité, d'isolation et de conformité dignes d'un SaaS B2B.

Chaque objectif se relie à un ou plusieurs [JTBD](../01-discovery/jobs-to-be-done.md) et se mesure via l'[arbre de métriques](../00-vision/north-star-metric.md).

## 2. Périmètre

**Dans le périmètre (v1)** : les 5 domaines produit — CRM, Inbox/Communication, Bob (copilote agentique), Knowledge Base, Platform (workflows/analytics/usage) — plus les fondations transverses (auth, multi-tenant, RBAC, observabilité).

**Détail par domaine** : chaque domaine a sa **spec dédiée** dans [`specs-domaines/`](specs-domaines/). Ce PRD en donne la vue consolidée et les exigences.

## 3. Utilisateurs & rôles

Voir [Personas](../01-discovery/personas.md). Modèle de rôles observé dans le code :

- **Modèle RBAC** : `Permission` (globale, `resource:action`) → `Role` (tenant-scoped, `is_system` pour les rôles immuables) → `UserRole` (assignation). Rôles système : Admin, Member, Viewer. Rôles custom possibles par tenant.
- **Super-admin** : `is_super_admin = true` → accès cross-tenant (gestion des tenants, usage global).
- **Contexte utilisateur** : un utilisateur appartient à **un** `tenant_id` (immuable) et opère avec une `active_organization_id` (contexte CRM sélectionnable).

| Rôle | Peut | Ne peut pas |
|---|---|---|
| Member | Utiliser CRM/inbox/Bob sur son tenant | Gérer les rôles, voir d'autres tenants |
| Admin | + gérer équipe, rôles, workflows, gouvernance d'outils, intégrations | Sortir de son tenant |
| Super-admin | + CRUD tenants, usage cross-tenant, rate cards | — |

**EF-RBAC-1** : toute action est autorisée selon les permissions du JWT ; un 403 renvoie l'utilisateur au dashboard (pas d'écran cassé).

## 4. Exigences fonctionnelles par domaine

> Convention : `EF-<DOMAINE>-<n>`. Priorité **MoSCoW** : **M**ust / **S**hould / **C**ould. Statut : ✅ implémenté · 🟡 partiel · ⛔ à faire (selon la cartographie du code).

### 4.1 CRM → [spec détaillée](specs-domaines/crm.md)

| # | Exigence | Prio | Statut |
|---|---|---|---|
| EF-CRM-1 | Gérer des **contacts** (CRUD, recherche, pagination), rattachés à une organisation | M | ✅ |
| EF-CRM-2 | Gérer des **organisations** et départements (CRUD, statut, type) | M | ✅ |
| EF-CRM-3 | Gérer des **opportunités** sur un pipeline à 6 étapes, avec montant, probabilité, échéance | M | ✅ |
| EF-CRM-4 | Attacher des **lignes produits** à une opportunité (quantité, prix, remise) | M | ✅ |
| EF-CRM-5 | Générer des **devis** avec calcul subtotal / remise / taxe / total, et statut (DRAFT→ACCEPTED…) | M | ✅ |
| EF-CRM-6 | Gérer des **activités/tâches** multi-liées (contacts, orgs, opportunités) avec statut et échéance | M | ✅ |
| EF-CRM-7 | Gérer un **catalogue produits** multi-catégories (SaaS, service, add-on, consulting, hardware) | S | ✅ |
| EF-CRM-8 | **Enrichir** automatiquement contacts/organisations (Hunter, Bright Data, LinkedIn) | S | 🟡 |
| EF-CRM-9 | Fournir un **dashboard CRM** consolidé (totaux, highlights, next actions) par composition B4F | M | ✅ |
| EF-CRM-10 | Créer contact/opportunité **en langage naturel** via Bob | S | 🟡 |

### 4.2 Inbox / Communication → [spec détaillée](specs-domaines/inbox-communication.md)

| # | Exigence | Prio | Statut |
|---|---|---|---|
| EF-INB-1 | Synchroniser les emails via **Microsoft 365** et via **Pipedream** (Outlook/Gmail) | M | ✅ |
| EF-INB-2 | Recevoir des **webhooks entrants signés** (HMAC-SHA256) pour la sync temps réel | M | ✅ |
| EF-INB-3 | Rattacher automatiquement un email à un **contact** et une **organisation** | M | 🟡 |
| EF-INB-4 | Gérer des **smart labels** hiérarchiques (mots-clés + hint IA, couleur, parent) | M | ✅ |
| EF-INB-5 | Lister/filtrer les emails (dossier, label, non-lu, important, recherche plein texte) | M | ✅ |
| EF-INB-6 | **Composer / répondre / transférer** un email (via action Pipedream) | M | ✅ |
| EF-INB-7 | Vue **integration overview** (connexions actives + stats labels par provider) | S | ✅ |
| EF-INB-8 | Générer **résumé IA** et **action items** d'un email | C | 🟡 (champs présents côté MS365, à généraliser) |

### 4.3 Bob — copilote agentique → [spec détaillée](specs-domaines/bob-copilote.md)

| # | Exigence | Prio | Statut |
|---|---|---|---|
| EF-BOB-1 | Converser avec l'utilisateur en session (historique, idempotence client) | M | ✅ |
| EF-BOB-2 | Exécuter un **tool-call loop** (max 5 itérations, max 3 outils/itération, max 12 total) | M | ✅ |
| EF-BOB-3 | **Confirmer** toute action sensible (write/destructive) avant exécution, avec *readback* | M | ✅ |
| EF-BOB-4 | Router les intentions vers les capacités **MCP** de façon déterministe (avant LLM) | M | ✅ |
| EF-BOB-5 | Mémoire **RAG** privée/organisationnelle (scope + sensibilité), recherche vectorielle (Milvus) | M | 🟡 |
| EF-BOB-6 | **Gouvernance d'outils** à 2 niveaux : policies admin + préférences utilisateur | M | ✅ |
| EF-BOB-7 | Catalogue **agents / skills / tools** extensible (défauts + custom) | S | ✅ |
| EF-BOB-8 | Exposer **narration steps**, tool-calls, provider/modèle et coût de chaque run | M | ✅ |
| EF-BOB-9 | **Dégrader** vers un provider local si le LLM principal est indisponible | S | ✅ |
| EF-BOB-10 | **BCC** (Bob Control Center) : agents, skills, training, client map | S | 🟡 |
| EF-BOB-11 | Réglages de **personnalité** et de **voix** de Bob | C | 🟡 |

### 4.4 Knowledge Base → [spec détaillée](specs-domaines/knowledge-base.md)

| # | Exigence | Prio | Statut |
|---|---|---|---|
| EF-KB-1 | Gérer des **articles** (CRUD, slug, contenu, tags, visibilité, publication) | M | ✅ |
| EF-KB-2 | Organiser en **catégories** (icône, couleur, ordre, compteur d'articles) | M | ✅ |
| EF-KB-3 | **Rechercher** (plein texte titre/excerpt/tags) et filtrer (catégorie, visibilité) | M | ✅ |
| EF-KB-4 | Page **home KB** composée (catégories + récents + populaires + stats) | S | ✅ |
| EF-KB-5 | **Feedback** utile/pas utile par article + stats d'engagement (vues, helpfulness) | S | ✅ |
| EF-KB-6 | Contrôle d'accès par **visibilité** (internal/shared/public) + module/rôle requis | S | ✅ |
| EF-KB-7 | **Génération d'articles** assistée par LLM | C | ⛔ (non détecté ; hypothèse) |

### 4.5 Platform (workflows / analytics / usage) → [spec détaillée](specs-domaines/platform.md)

| # | Exigence | Prio | Statut |
|---|---|---|---|
| EF-PLT-1 | Définir des **workflows** à 4 niveaux (system/company/department/user), DAG de steps | M | ✅ |
| EF-PLT-2 | Déclencher un workflow **manuellement**, sur **événement**, ou **planifié** | M | 🟡 |
| EF-PLT-3 | Mode d'exécution réglable : **suggest / auto / require_approval** | M | ✅ |
| EF-PLT-4 | **Journaliser** chaque exécution et chaque step (statut, IO, durée, confidence) | M | ✅ |
| EF-PLT-5 | **Ledger d'usage** append-only par transaction (service, tokens, COGS, correlation) | M | ✅ |
| EF-PLT-6 | Vues **usage** self-service (tenant) et **admin** (cross-tenant, par intent) | M | ✅ |
| EF-PLT-7 | **Cost rate cards** historisées (prix unitaire par provider/modèle/période) | S | ✅ |
| EF-PLT-8 | **Dashboard analytics** (métriques CRM + plateforme) | S | 🟡 |

## 5. Exigences transverses

| # | Exigence |
|---|---|
| EF-X-1 | **Authentification** : login email/mot de passe, JWT access (24 h) + refresh (7 j), refresh auto sur 401, rate-limit login (5/15 min/IP). |
| EF-X-2 | **Multi-tenant** : `tenant_id` sur chaque entité, filtré à chaque requête ; jamais de fuite inter-tenant (sévérité max). |
| EF-X-3 | **Sélection d'organisation active** : l'utilisateur bascule de contexte CRM sans re-login. |
| EF-X-4 | **Audit & soft-delete** : `created_at/by`, `updated_at`, `deleted_at/by` ; aucune suppression physique par défaut. |
| EF-X-5 | **Event Bus** : toute synchro inter-backend passe par Redis (`<service>.<entity>.<action>`), jamais en HTTP direct. |
| EF-X-6 | **Traçabilité** : `trace_id` (W3C) propagé HTTP + events + logs ; chaque run/transaction corrélable. |
| EF-X-7 | **Idempotence** : clés d'idempotence sur les écritures sensibles (message, run, confirmation). |

## 6. Exigences non-fonctionnelles (ENF)

| # | Catégorie | Exigence | Référence |
|---|---|---|---|
| ENF-1 | **Architecture** | Séparation stricte B4F (logique) / Backend (CRUD 1 entité) ; Clean Architecture (import-linter) | [v1.4](../regles-architecture-deploiement.md) |
| ENF-2 | **Sécurité** | HTTPS partout, TLS wildcard, backends non exposés, secrets hors repo, JWT signé | [Threat Model](../04-technique/threat-model.md) |
| ENF-3 | **Isolation** | `tenant_id` obligatoire ; PgBouncer transaction mode ; requêtes qualifiées par schéma | [Data Model](../04-technique/data-model.md) |
| ENF-4 | **Fiabilité** | Dégradation propre (provider LLM, Milvus) ; runs échoués < 2 % ; probes liveness/readiness/startup | [SLO](../04-technique/slo-observability.md) |
| ENF-5 | **Performance** | Dashboard par composition parallèle (asyncio) ; budgets frontend (bundle < 1 Mo) ; latence run cible P95 | [SLO](../04-technique/slo-observability.md) |
| ENF-6 | **Observabilité** | Logs JSON structurés (structlog), traces OTel → Alloy, `/health` avec dépendances, `/metrics` Prometheus | [SLO](../04-technique/slo-observability.md) |
| ENF-7 | **Qualité** | Couverture tests ≥ 85 % (back & front), import-linter 0 violation, E2E Playwright | [Plan technique](../05-delivery/plan-technique.md) |
| ENF-8 | **Déployabilité** | CI/CD GitLab parent/child, images Kaniko + scan Trivy + signature Cosign, Helm sur K8s, migrations Alembic via Lease | [System Design](../04-technique/system-design-doc.md) |
| ENF-9 | **Conformité** | RGPD : donnée tenant-scoped, sensibilité typée, rétention (`expires_at`), droit à l'effacement | [DPIA](../06-gouvernance/privacy-dpia.md) |
| ENF-10 | **Coût** | COGS par action mesuré (ledger + rate cards) ; budget d'inférence maîtrisé (limites tool-loop) | [North Star](../00-vision/north-star-metric.md) |
| ENF-11 | **Sûreté IA** | Aucune action irréversible sans confirmation ; gouvernance d'outils par risque/scope ; sensibilité RAG respectée | [Tenets](../00-vision/tenets.md) |

## 7. Contraintes & hypothèses

**Contraintes techniques** (imposées par l'existant) :
- Stack figée : FastAPI (Python), SQLAlchemy + Alembic, PostgreSQL 16, Redis, Angular 21 + NGRX.
- Norme d'architecture **v1.4** (contrat d'ingénierie non négociable).
- Fournisseurs : LLM via **Fireworks** (modèle `kimi-k2p7-code`), embeddings `qwen3-embedding-8b`, intégrations via **Pipedream**, vecteurs via **Milvus** (optionnel en local).
- 7 B4F + 14 backends + frontend = **22 services** à opérer.

**Hypothèses** `[À VALIDER]` :
- Le client cible est sous Microsoft 365.
- Le business model est abonnement par siège + usage IA (déduit du ledger et des plans).
- Le marché initial est la PME B2B francophone (Canada/Europe).

## 8. Critères d'acceptation & métriques

Le produit est « bon » quand :
- **CA-1** : un nouvel utilisateur atteint sa **1ʳᵉ action Bob validée** rapidement (*time-to-first-value*), voir NSM.
- **CA-2** : le **taux de confirmation** (proposé→validé) est élevé (Bob propose des actions pertinentes).
- **CA-3** : le **taux d'annulation au gate** et le **taux d'action reprise** sont bas (qualité).
- **CA-4** : **zéro** fuite inter-tenant ; **zéro** action irréversible sans confirmation.
- **CA-5** : runs échoués/dégradés < 2 % ; latence run P95 sous cible.
- **CA-6** : couverture tests ≥ 85 %, import-linter vert, pipeline CI/CD vert.

Détail des métriques : [North Star Metric](../00-vision/north-star-metric.md) · [OKR](okr.md).

## 9. Hors périmètre & questions ouvertes

**Hors périmètre v1** : mobile natif, marketplace de skills tierce, mode voix production (`voice_phone` amorcé mais non finalisé), génération d'articles KB par LLM, multi-devise avancée.

**Questions ouvertes** (à trancher — voir [Decision Log](../06-gouvernance/decision-log.md)) :
- **Q1** : `[À VALIDER]` Modèle de tarification définitif (siège + usage ? seuils ?).
- **Q2** : Quand basculer des workflows en mode `auto` par défaut (quel niveau de risque acceptable) ?
- **Q3** : Stratégie de migration des tables `membrane_*` vers un nommage définitif.
- **Q4** : Généralisation du résumé/action-items IA à tous les providers email.
- **Q5** : Priorité relative BCC/multi-agents vs approfondissement du cœur.

> Ce PRD est **vivant** : chaque nouvelle feature majeure doit y ajouter/mettre à jour une exigence, et référencer l'ADR correspondant.
