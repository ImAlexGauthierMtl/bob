# Template: Module CRUD Full-Stack

> Recette pour créer un module CRUD complet (backend + frontend) en une séquence.
> **Zéro décision** : exécuter les templates dans cet ordre exact.

## Input requis

| Paramètre | Exemple |
|-----------|---------|
| `RESOURCE` (PascalCase) | `Account` |
| `resource` (snake_case) | `account` |
| `resources` (pluriel) | `accounts` |
| `LABEL_SINGULAR` (FR) | `Compte` |
| `LABEL_PLURAL` (FR) | `Comptes` |
| `FIELDS` | Liste nom:type |
| `ICON` (FA) | `fa-building` |

## Séquence d'exécution (dans cet ordre STRICT)

### Étape 1 — Backend Model
→ `templates/code/backend/model-sqlalchemy/TEMPLATE.md`
- Créer le modèle SQLAlchemy
- Ajouter les re-exports dans `models.py`

### Étape 2 — Backend Schemas
→ `templates/code/backend/schemas-pydantic/TEMPLATE.md`
- Créer Base, Create, Update, Response
- Ajouter les re-exports dans `schemas.py`

### Étape 3 — Migration Alembic
```bash
cd backend
alembic revision --autogenerate -m "add {resources} table"
alembic upgrade head
```

### Étape 4 — Backend Router
→ `templates/code/backend/router-crud/TEMPLATE.md`
- Créer le router CRUD (5 endpoints)
- Enregistrer dans `main.py`

### Étape 5 — Backend Tests
- Tester les 6 cas (list, create, get, get_404, update, delete)
```bash
python -m pytest tests/test_{resources}.py -v
```

### Étape 6 — Frontend Model
→ `templates/code/frontend/model-typescript/TEMPLATE.md`
- Créer l'interface TS + DTOs

### Étape 7 — Frontend Service
→ `templates/code/frontend/service-http/TEMPLATE.md`
- Créer le service HTTP (5 méthodes)

### Étape 8 — Frontend Store NGRX (optionnel si simple)
→ `templates/code/frontend/store-ngrx/TEMPLATE.md`
- Créer les 5 fichiers du store

### Étape 9 — Frontend Page Liste
→ `templates/code/frontend/page-list/TEMPLATE.md`
- Créer la page liste

### Étape 10 — Frontend Route
- Ajouter les routes dans `app.routes.ts`

### Étape 11 — Vérification
```bash
# Backend
python -m pytest tests/ -v --tb=short

# Frontend
npx ng build --configuration=development
```

## Résultat attendu

```
backend/
├── core/{domain}/models.py     ← +1 modèle
├── core/{domain}/schemas.py    ← +4 schemas
├── routers/{resources}.py      ← nouv. router CRUD
├── tests/test_{resources}.py   ← 6 tests
└── migrations/versions/xxx.py  ← migration

frontend/src/app/
├── models/{resource}.model.ts  ← interface + DTOs
├── services/{resource}.service.ts ← CRUD HTTP
├── store/{resources}/          ← 5 fichiers NGRX
└── pages/authenticated/{resources}/{resources}.page.ts ← liste
```
