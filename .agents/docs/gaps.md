# Gaps détectés — Registre UNRULED + Normes à écrire

> Ce registre se remplit **systématiquement** à chaque implémentation.
> Chaque gap = une future norme/skill/rule que les ingénieurs doivent écrire.
>
> **Deux sections** :
> 1. **Templates manquants** — gaps au niveau du framework (normes à créer)
> 2. **Décisions UNRULED** — ce que le LLM a décidé seul, avec justification

---

## Templates manquants

| Date | Source | Description du gap | Type | Priorité | Status |
|------|--------|--------------------|------|----------|--------|
| 2026-03-06 | Post-mortem zoneless | Pas de template `bootstrap-angular/TEMPLATE.md` avec `app.config.ts` | Template | 🔴 HAUTE | À faire |
| 2026-03-06 | Post-mortem zoneless | Pas de template `auth-flow/TEMPLATE.md` avec interceptor queue | Template | 🔴 HAUTE | À faire |
| 2026-03-06 | Post-mortem zoneless | `/nouveau-projet` ne valide pas zone.js après scaffold Angular 21+ | Workflow | 🔴 HAUTE | À faire |
| 2026-03-06 | Post-mortem zoneless | Pas de σ-trigger `FRAMEWORK_MAJOR_SHIFT` dans Delta-point | Protocole | 🟡 MOYENNE | À faire |

---

## Décisions UNRULED — Journal des implémentations sans template

> [!IMPORTANT]
> **Obligation** : Chaque fois que le LLM crée du code sans template correspondant, il DOIT ajouter une entrée ici.
> Le format ci-dessous est NON-NÉGOCIABLE.

### Format d'entrée obligatoire

```markdown
### [DATE] — [fichier créé] — [action]

**Template cherché** : [quel template a été cherché et n'a pas été trouvé]
**Template le plus proche** : [quel template existant a été utilisé comme base]
**Décision LLM** : [ce que le LLM a décidé de faire]
**Justification** : [pourquoi cette approche, comment elle s'aligne avec les patterns existants]
**Règles respectées** : [quelles règles NON-NÉGOCIABLES d'autres templates ont été suivies]
**Écart assumé** : [ce qui diffère des patterns établis et pourquoi]
```

---

### 2026-03-08 — `settings-team.html` — Dropdown menu admin sur carte usager

**Template cherché** : `templates/code/frontend/component-dropdown/` — n'existe pas
**Template le plus proche** : `templates/code/frontend/component-dialog/` (overlay + boutons)
**Décision LLM** : Menu dropdown positionné en absolu sous le bouton ⋮, avec 3 actions (Change Role, Reset Password, Deactivate)
**Justification** : Pattern identique aux context menus des apps SaaS (Zoho, HubSpot). Réutilise les classes CSS existantes de `settings-shared.css` (`.team-card__action`, `.btn`)
**Règles respectées** : `standalone: true`, `inject()` (corrigé après audit), labels FR (corrigé après audit), `track item.id` dans `@for`
**Écart assumé** : Pas de signal input/output comme dans le template dialog — le dropdown est intégré directement dans le composant parent car il partage l'état (liste d'utilisateurs). Un composant séparé aurait ajouté de la complexité sans bénéfice ici.

---

### 2026-03-08 — `settings-roles/` — Page gestion des rôles et permissions

**Template cherché** : `templates/code/frontend/page-settings/` — n'existe pas
**Template le plus proche** : `templates/code/frontend/page-list/` (structure liste + CRUD)
**Décision LLM** : Composant settings-panel avec cards rôles + 3 dialogs (créer, modifier, permissions matrix)
**Justification** : Suit le pattern `page-list` pour la structure (loading → error → list → empty), adapté au contexte settings qui utilise `settings-shared.css` au lieu du layout standard flex/table
**Règles respectées** : `inject()`, `loadItems`/`createItem`/`deleteItem`, loading state, error state + Réessayer, empty state, labels FR, `track item.id`
**Écart assumé** : Pas de table avec colonnes (template page-list) → cards à la place, car cohérent avec le pattern visuel de `settings-team` déjà en place. La matrice de permissions (checkboxes groupées par ressource) n'a aucun template — implémentée avec un pattern toggle-all inspiré des panels d'admin Firebase/AWS IAM.

---

### 2026-03-08 — `role.service.ts` — Service HTTP pour les rôles

**Template cherché** : `templates/code/frontend/service-http/`  ✅ trouvé
**Décision LLM** : Template suivi + 2 méthodes supplémentaires (`getPermissions`, `setPermissions`)
**Justification** : Le template ne couvre que les 5 méthodes CRUD standard. L'API RBAC a 2 endpoints supplémentaires (permissions listing + assignment) qui nécessitent des méthodes dédiées.
**Règles respectées** : `inject(HttpClient)`, `environment.apiUrl`, `Observable<T>` retourné, pas de `.subscribe()` dans le service, nommage `getAll`/`getById`/`create`/`update`/`delete`
**Écart assumé** : 2 méthodes hors template (`getPermissions`, `setPermissions`). Nommage aligné sur la sémantique métier plutôt que le pattern CRUD car ces actions ne sont pas des CRUD sur la ressource Role elle-même.

---

### 2026-03-08 — `backend/user_routes.py` — Route PATCH admin update user

**Template cherché** : `templates/code/backend/router-crud/` ✅ trouvé
**Décision LLM** : Ajout d'un endpoint PATCH au router existant (pas un nouveau router)
**Justification** : Le router `user_routes.py` existait déjà avec GET/POST/DELETE. Le template prescrit un router complet avec 5 endpoints — ici on ajoute seulement le PATCH manquant au router existant.
**Règles respectées** : `response_model=UserResponse`, `model_dump(exclude_unset=True)` pour l'update partiel, 404 `HTTPException` si ressource non trouvée, tenant isolation (vérifie `tenant_id`)
**Écart assumé** : Pas de use case dédié (`UpdateUserByAdminUseCase`) — logique directe dans la route car l'action est simple (setattr + commit). Le template use-case prescrit un fichier séparé mais l'overhead n'est pas justifié pour 3 lignes de logique.
