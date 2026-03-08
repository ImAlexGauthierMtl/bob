# Pré-vol Templates — Checklist obligatoire

> **QUAND** : Avant de créer ou modifier tout fichier de code (`.ts`, `.py`, `.html`, `.css`).
> **QUI** : Tout agent IA (Cursor, Gemini, Claude, GPT...) travaillant dans ce projet.
> **POURQUOI** : Garantir la conformité aux patterns établis, éliminer la dette technique à la source.

---

## Checklist (dans l'ordre)

### 1. Identifier le type de fichier à créer

| Type | Templates à vérifier |
|------|---------------------|
| Modèle SQLAlchemy | `templates/code/backend/model-sqlalchemy/` |
| Schema Pydantic | `templates/code/backend/schemas-pydantic/` |
| Repository | `templates/code/backend/repository-pattern/` |
| Use Case | `templates/code/backend/use-case/` |
| Router CRUD | `templates/code/backend/router-crud/` |
| Interface TS | `templates/code/frontend/model-typescript/` |
| Service HTTP | `templates/code/frontend/service-http/` |
| Page liste | `templates/code/frontend/page-list/` |
| Page détail | `templates/code/frontend/page-detail/` |
| Dialog | `templates/code/frontend/component-dialog/` |
| Badge | `templates/code/frontend/component-badge/` |

### 2. Lire le `TEMPLATE.md` correspondant

```
cat .agents/templates/code/{backend|frontend}/{template-name}/TEMPLATE.md
```

### 3. Extraire les règles NON-NÉGOCIABLES

Chaque template contient une section **Règles NON-NÉGOCIABLES**. Les lister avant de coder.

### 4. Catégoriser : RULED vs UNRULED

| Catégorie | Action |
|-----------|--------|
| ✅ **RULED** | Template trouvé → suivre **pas-à-pas** |
| ⚠️ **UNRULED** | Pas de template → signaler clairement à l'utilisateur, ajouter dans `docs/gaps.md` |

### 5. Coder en suivant le template

**Règles clés extraites des templates existants :**

#### Backend Python
- `model_dump(exclude_unset=True)` pour les updates partiels
- `response_model` sur chaque endpoint
- `status_code=201` POST, `status_code=204` DELETE
- Repository : `is_deleted == False` dans toutes les queries
- Use case : 1 fichier = 1 classe = 1 `execute()`
- Schemas : `Base` → `Create(Base)` → `Update(BaseModel, tout Optional)` → `Response(Base + id + timestamps)`

#### Frontend TypeScript
- `inject()` — **jamais** constructor injection
- `Injectable({ providedIn: 'root' })` — toujours root
- Nommage service : `getAll()`, `getById()`, `create()`, `update()`, `delete()`
- Modèle dans fichier séparé `*.model.ts`
- `UpdateDto = Partial<CreateDto>`
- Enums = type union (pas `enum`)
- Dates = `string` (ISO)
- UI labels en **français**
- Loading state + Error state + Empty state — **toujours**
- `track item.id` dans `@for`

### 6. Signaler le résultat

À la fin de chaque implémentation, indiquer :
```
📋 Conformité templates :
  ✅ RULED : [liste des templates suivis]
  ⚠️ UNRULED : [liste des actions sans template + raison]
```

---

## Post-mortem — Incident 2026-03-08

**Ce qui s'est passé** : Le LLM a créé `RoleService`, `SettingsRolesComponent`, et les fichiers HTML/CSS sans consulter aucun des 72 templates disponibles.

**Violations détectées** :
- `constructor(private ...)` au lieu de `inject()`
- Nommage `listRoles()` au lieu de `getAll()`
- Modèles dans le fichier service au lieu d'un `*.model.ts` séparé
- Labels UI en anglais au lieu du français
- Pas d'error state avec bouton Réessayer

**Cause racine** : Aucun mécanisme ne forçait la vérification des templates quand la demande ne passait pas par `/feature`.

**Correction** : Cette checklist + règle dans `HDQ.md`.
