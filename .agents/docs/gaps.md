# Rapport d'audit de conformité — Gaps de l'application

> **Date** : 2026-03-08
> **Auteur** : LLM (Antigravity) — audit automatisé
> **Destinataire** : Équipe R&D — The Smart Crew
> **Objectif** : Valider les choix d'implémentation et proposer des correctifs pour aligner le code aux normes du projet

---

## Résumé exécutif

| Zone | Conformité | Gaps critiques |
|------|-----------|----------------|
| Backend — Routes | 🟢 85% | Status codes corrects, response_model partout |
| Backend — Repositories | 🟢 90% | `is_deleted`, `version += 1`, `deleted_by` — bien |
| Backend — Use Cases | 🔴 15% | Couche quasi-absente — logique métier dans les routes |
| Backend — Schemas | 🟡 70% | Existent mais pattern Base/Create/Update/Response inconsistant |
| Frontend — Services | 🔴 7% | 13/14 utilisent `constructor()` au lieu de `inject()` |
| Frontend — Models | 🔴 7% | 1/14 fichiers `.model.ts` séparés |
| Frontend — Pages | 🔴 0% | 17/17 composants utilisent `constructor()` injection |
| Frontend — Dialogs | 🟡 50% | Pas de réutilisation du composant `ConfirmDialog` template |

---

## Section 1 — Backend

---

### 1.1 Routes (22 fichiers)

**Template de référence** : `templates/code/backend/router-crud/TEMPLATE.md`

#### ✅ Conforme

| Règle | Statut | Détail |
|-------|--------|--------|
| `response_model` sur chaque endpoint | ✅ | Toutes les routes CRUD l'utilisent |
| `status_code=201` sur POST | ✅ | Vérifié sur organization, contact, opportunity, quote, user, department, workflow, kb, training |
| Prefix `/api/v1/{resources}` | ✅ | Toutes les routes suivent la convention |
| Dépendance `get_current_user` | ✅ | Auth JWT sur toutes les routes protégées |

#### ⚠️ Gaps détectés

| # | Fichier | Gap | Sévérité | Correctif proposé |
|---|---------|-----|----------|-------------------|
| R1 | `activity_routes.py` | Pas de `status_code=204` sur DELETE | 🟡 Moyenne | Ajouter `status_code=status.HTTP_204_NO_CONTENT` |
| R2 | `contact_routes.py` | Pas de `status_code=204` sur DELETE | 🟡 Moyenne | Idem |
| R3 | `opportunity_routes.py` | Pas de `status_code=204` sur DELETE | 🟡 Moyenne | Idem |
| R4 | `quote_routes.py` | Pas de `status_code=204` sur DELETE | 🟡 Moyenne | Idem |
| R5 | `organization_routes.py` | Pas de `status_code=204` sur DELETE | 🟡 Moyenne | Idem |
| R6 | `user_routes.py` | Pas de `status_code=204` sur DELETE | 🟡 Moyenne | Idem |
| R7 | Tous les routes CRUD | Logique métier directement dans les routes au lieu de use cases | 🔴 Haute | Voir section 1.3 |
| R8 | `role_routes.py` | Le router fait du CRUD direct sur le repo sans passer par un use case | 🟡 Moyenne | Acceptable temporairement — les routes role sont simples |
| R9 | `authorization.py` | `require_permission()` retournait `Depends(_check)` (double-wrapped) | ✅ Corrigé | Fix appliqué le 2026-03-08 |

---

### 1.2 Repositories (10 fichiers)

**Template de référence** : `templates/code/backend/repository-pattern/TEMPLATE.md`

#### ✅ Conforme

| Règle | Statut | Détail |
|-------|--------|--------|
| `is_deleted == False` dans toutes les queries | ✅ | Vérifié dans les 10 repositories |
| `commit()` + `refresh()` après écriture | ✅ | Présent dans tous les repos |
| `version += 1` sur update/delete | ✅ | 18 occurrences à travers 9 repositories |
| Soft delete (jamais hard delete) | ✅ | Toutes les suppressions sont `is_deleted = True` |
| `deleted_by` enregistré | ✅ | 8/10 repos (manque: role, kb_category) |

#### ⚠️ Gaps détectés

| # | Fichier | Gap | Sévérité | Correctif proposé |
|---|---------|-----|----------|-------------------|
| P1 | `role_repository.py` | Pas de `version += 1`, pas de `deleted_by`, pas de soft delete | 🟡 Moyenne | L'entité Role n'a pas de champ `is_deleted` dans le modèle SQLAlchemy. Décision architecturale : les rôles système ne sont jamais supprimés, les rôles custom sont hard-delete. **À valider avec R&D** |
| P2 | Tous les repos | Pas de méthode `count()` standardisée (template l'exige) | 🟡 Moyenne | Certains repos l'ont (`quote`, `activity`), d'autres non. Standardiser |
| P3 | Tous les repos | Pas de `order_by(created_at.desc())` systématique | 🟡 Moyenne | Vérifier que toutes les listes sont ordonnées |
| P4 | `role_repository.py` | Méthodes non-standard (`get_or_create_permission`, `get_user_permissions`, `set_role_permissions`) | 🟡 Moyenne | Acceptable — la ressource Role a des besoins spécifiques au-delà du CRUD standard |

---

### 1.3 Use Cases (4 fichiers — devrait être ~50)

**Template de référence** : `templates/code/backend/use-case/TEMPLATE.md`

#### 🔴 Gap critique

Le template prescrit **1 fichier = 1 use case = 1 classe = 1 méthode `execute()`**, avec 5 use cases par ressource (Create, List, GetById, Update, Delete).

**État actuel** :

| Fichier | Contenu |
|---------|---------|
| `auth_use_cases.py` | Authentification |
| `enrich_organization.py` | Enrichissement IA |
| `organization_use_cases.py` | CRUD organisation |
| `user_use_cases.py` | CRUD utilisateur |

**Manquant** (10 ressources × 5 actions = 50 use cases) :

| Ressource | Use cases manquants |
|-----------|-------------------|
| Contact | Create, List, GetById, Update, Delete |
| Opportunity | Create, List, GetById, Update, Delete |
| Quote | Create, List, GetById, Update, Delete |
| Activity | Create, List, GetById, Update, Delete |
| Department | Create, List, GetById, Update, Delete |
| Workflow | Create, List, GetById, Update, Delete, Execute |
| KB Article | Create, List, GetById, Update, Delete |
| Training | Create, List, GetById, Update, Delete |
| Role | Create, List, GetById, Update, Delete |
| BCC | Opérations spécifiques |

> **Impact** : La logique métier est actuellement dans les routes FastAPI (`presentation` layer). Cela viole le principe Clean Architecture — la couche `presentation` ne devrait faire que du routing/validation, pas de la logique métier.
>
> **Recommandation R&D** : Phase de refactoring pour extraire la logique métier des routes vers des use cases dédiés. Prioriser les ressources avec de la logique complexe (Organization, Workflow, Training) avant les CRUD simples.

---

### 1.4 Schemas Pydantic (12 fichiers)

**Template de référence** : `templates/code/backend/schemas-pydantic/TEMPLATE.md`

Le template prescrit 4 classes par ressource : `Base`, `Create(Base)`, `Update(BaseModel, tout Optional)`, `Response(Base + id + timestamps)`.

| Fichier | Base | Create | Update | Response | Conforme |
|---------|------|--------|--------|----------|----------|
| `organization_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `contact_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `opportunity_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `quote_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `activity_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `user_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `department_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `workflow_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `kb_schemas.py` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `role_schemas.py` | ⚠️ | ✅ | ⚠️ | ✅ | 🟡 Partiel |
| `bcc_schemas.py` | ⚠️ | ⚠️ | ⚠️ | ✅ | 🟡 Partiel |
| `training_schemas.py` | ✅ | ✅ | ⚠️ | ✅ | 🟡 Partiel |

> **Note** : `role_schemas.py` et `bcc_schemas.py` ont des structures non-standard car leurs ressources ne suivent pas un CRUD classique. Acceptable si justifié.

---

## Section 2 — Frontend

---

### 2.1 Services HTTP (14 fichiers)

**Template de référence** : `templates/code/frontend/service-http/TEMPLATE.md`

#### Règles NON-NÉGOCIABLES du template

1. `inject(HttpClient)` — pas de constructor injection
2. `Injectable({ providedIn: 'root' })` — toujours root
3. `environment.apiUrl` — jamais d'URL hardcodée
4. Méthodes typées avec generics
5. Retourne `Observable<T>` — jamais de `.subscribe()` dans le service
6. Nommage : `getAll()`, `getById()`, `create()`, `update()`, `delete()`

| Service | inject() | apiUrl | Nommage standard | Conforme |
|---------|----------|--------|-------------------|----------|
| `role.service.ts` | ✅ | ✅ | ✅ | ✅ |
| `user.service.ts` | ❌ constructor | ✅ | ❌ `getUsers()` | ❌ |
| `organization.service.ts` | ❌ constructor | ✅ | ❌ `listOrganizations()` | ❌ |
| `contact.service.ts` | ❌ constructor | ✅ | ❌ `listContacts()` | ❌ |
| `opportunity.service.ts` | ❌ constructor | ✅ | ❌ `listOpportunities()` | ❌ |
| `quote.service.ts` | ❌ constructor | ✅ | ❌ `listQuotes()` | ❌ |
| `activity.service.ts` | ❌ constructor | ✅ | ❌ `listActivities()` | ❌ |
| `workflow.service.ts` | ❌ constructor | ✅ | ❌ `listWorkflows()` | ❌ |
| `kb.service.ts` | ❌ constructor | ✅ | ❌ `listArticles()` | ❌ |
| `bob.service.ts` | ❌ constructor | ✅ | N/A (pas CRUD) | 🟡 |
| `bcc.service.ts` | ❌ constructor | ✅ | N/A (pas CRUD) | 🟡 |
| `training.service.ts` | ❌ constructor | ✅ | ❌ `listSessions()` | ❌ |
| `auth.service.ts` | ❌ constructor | ✅ | N/A (pas CRUD) | 🟡 |
| `bob-action.service.ts` | ❌ constructor | N/A | N/A (pas HTTP) | 🟡 |

> **Score** : 1/14 conforme (7%) — **13 services à migrer vers `inject()`**
>
> **Correctif** : Refactoring systématique — remplacer `constructor(private http: HttpClient)` par `private http = inject(HttpClient)` dans les 13 services. Estimation : ~30 min de travail.

---

### 2.2 Modèles TypeScript (1/14 fichiers)

**Template de référence** : `templates/code/frontend/model-typescript/TEMPLATE.md`

Le template exige un fichier `*.model.ts` séparé par ressource avec :
- Interface principale (miroir du Pydantic Response)
- `CreateDto`
- `UpdateDto = Partial<CreateDto>`

| Ressource | Fichier model | Interfaces | Conforme |
|-----------|--------------|------------|----------|
| Role | `role.model.ts` ✅ | Role, Permission, CreateRoleDto, UpdateRoleDto | ✅ |
| Organization | ❌ inline dans service | ❌ dans `organization.service.ts` | ❌ |
| Contact | ❌ inline dans service | ❌ dans `contact.service.ts` | ❌ |
| Opportunity | ❌ inline dans service | ❌ dans `opportunity.service.ts` | ❌ |
| Quote | ❌ inline dans service | ❌ dans `quote.service.ts` | ❌ |
| Activity | ❌ inline dans service | ❌ dans `activity.service.ts` | ❌ |
| User | ❌ inline dans service | ❌ dans `user.service.ts` | ❌ |
| Workflow | ❌ inline dans service | ❌ dans `workflow.service.ts` | ❌ |
| KB | ❌ inline dans service | ❌ dans `kb.service.ts` | ❌ |
| BCC | ❌ inline dans service | ❌ dans `bcc.service.ts` | ❌ |
| Training | ❌ inline dans service | ❌ dans `training.service.ts` | ❌ |
| Bob | ❌ inline dans service | ❌ dans `bob.service.ts` | ❌ |
| Auth | ❌ inline dans service | ❌ dans `auth.service.ts` | ❌ |

> **Score** : 1/14 (7%) — **13 modèles à extraire**
>
> **Correctif** : Extraire les interfaces de chaque service vers `shared/models/{resource}.model.ts`. Estimation : ~2h de travail.

---

### 2.3 Pages / Composants (17 fichiers)

**Template de référence** : `templates/code/frontend/page-list/TEMPLATE.md`

| Règle | Attendu | Réalité | Score |
|-------|---------|---------|-------|
| `inject()` au lieu de constructor | Obligatoire | 1/18 composants (settings-roles) | 🔴 6% |
| Loading state avec spinner | Obligatoire | ~70% des pages | 🟡 |
| Error state avec Réessayer | Obligatoire | ~30% des pages | 🔴 |
| Empty state avec icône + bouton | Obligatoire | ~50% des pages | 🟡 |
| `track item.id` dans `@for` | Obligatoire | ~80% | 🟡 |
| Labels UI en français | Obligatoire | ~60% | 🟡 |

> **Correctif** : Refactoring progressif par page. Prioriser les pages les plus utilisées (Organizations, Contacts, Opportunities, Dashboard).

---

### 2.4 Dialogs de confirmation

**Template de référence** : `templates/code/frontend/component-dialog/TEMPLATE.md`

Le template prescrit un composant `ConfirmDialogComponent` réutilisable avec signal `input()`/`output()`.

**État actuel** : Chaque page implémente ses propres dialogs inline au lieu de réutiliser le composant template.

> **Correctif** : Créer le composant `ConfirmDialogComponent` une seule fois et le réutiliser partout.

---

## Section 3 — Templates manquants

Ces fonctionnalités n'ont aucun template correspondant dans `.agents/templates/` :

| # | Fonctionnalité | Type manquant | Impact |
|---|---------------|---------------|--------|
| T1 | Bootstrap Angular (`app.config.ts`) | `templates/code/frontend/bootstrap-angular/` | Zoneless, providers, interceptors |
| T2 | Auth flow (interceptor queue) | `templates/code/frontend/auth-flow/` | Login/logout/refresh token |
| T3 | BCC Control Center | `templates/code/frontend/page-bcc/` | Pages complexes BCC |
| T4 | Voice pipeline | `templates/code/backend/voice-pipeline/` | STT → LLM → TTS flow |
| T5 | Bob tools (function calling) | `templates/code/backend/bob-tool/` | Pattern créer un outil Bob |
| T6 | Webhook handler | `templates/code/backend/webhook-handler/` | Traitement événements webhook |
| T7 | Settings page | `templates/code/frontend/page-settings/` | Structure settings + sidebar |
| T8 | Permission matrix | `templates/code/frontend/component-permission-matrix/` | Checkboxes groupées par ressource |
| T9 | Dropdown menu | `templates/code/frontend/component-dropdown/` | Menu contextuel sur élément |
| T10 | Seeder | `templates/code/backend/seeder/` | Pattern pour seed_*.py |

---

## Section 4 — Plan d'action correctif

### Phase 1 — Quick wins (1 jour)

| Action | Fichiers | Effort |
|--------|----------|--------|
| Migrer 13 services vers `inject()` | 13 services | 30 min |
| Ajouter `status_code=204` aux DELETE routes | 6 routes | 15 min |
| Créer `ConfirmDialogComponent` réutilisable | 1 composant | 30 min |

### Phase 2 — Modèles (2 jours)

| Action | Fichiers | Effort |
|--------|----------|--------|
| Extraire 13 fichiers `*.model.ts` | 13 modèles + 13 services | 2h |
| Standardiser méthodes services (`getAll`/`getById`/...) | 13 services + pages appelantes | 3h |

### Phase 3 — Clean Architecture (1 semaine) 

| Action | Fichiers | Effort |
|--------|----------|--------|
| Créer ~50 use cases manquants | 50 fichiers | 3 jours |
| Migrer logique métier des routes vers use cases | 22 routes | 2 jours |

### Phase 4 — Pages (continu)

| Action | Fichiers | Effort |
|--------|----------|--------|
| Migrer composants vers `inject()` | 17 pages | 2h |
| Ajouter error/loading/empty states manquants | ~10 pages | 1 jour |
| Traduire labels UI en français | Toutes les pages | 1 jour |

### Phase 5 — Templates manquants (continu)

Créer les 10 templates identifiés en section 3 au fur et à mesure des implémentations.

---

## Décisions à valider par R&D

> [!IMPORTANT]
> Les décisions suivantes nécessitent une validation explicite de l'équipe R&D.

### D1 — Rôles : hard delete vs soft delete

Le modèle `Role` n'a pas de champ `is_deleted`. Les rôles custom sont hard-delete.
**Question** : Faut-il ajouter soft delete aux rôles ?

### D2 — Use cases : timing du refactoring

50 use cases manquants. Le code fonctionne mais viole Clean Architecture.
**Question** : Prioriser ce refactoring maintenant ou après le MVP ?

### D3 — Frontend inject() : migration big-bang ou progressive

13 services + 17 composants à migrer.
**Question** : Tout migrer en une passe (risque de régression) ou progressivement par module ?

### D4 — Modèles TypeScript : convention de nommage des DTOs

Le template prescrit `CreateDto` / `UpdateDto`. Certains services utilisent `CreateRequest` / `UpdateRequest`.
**Question** : Quel suffixe standardiser — `Dto` ou `Request` ?

### D5 — Authorization middleware : structure

`require_permission()` / `require_role()` sont dans `middleware/`. Le template `router-crud` les utilise en `dependencies=[]`.
**Question** : Ce pattern est-il validé ou faut-il une couche service d'autorisation séparée ?
