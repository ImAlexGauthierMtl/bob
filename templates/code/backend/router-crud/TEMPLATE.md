# Template: Router CRUD FastAPI

> Recette pour créer un router CRUD complet avec 5 endpoints.
> **Zéro décision** : copier-adapter ce pattern exact.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Account` |
| `resource` | Nom (snake_case) | `account` |
| `resources` | Pluriel (snake_case) | `accounts` |

## Fichier à créer

`backend/routers/{resources}.py`

## Code exact

```python
""\"Router: {resources}\""\"

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import {Resource}
from schemas import {Resource}Create, {Resource}Response, {Resource}Update


router = APIRouter(tags=["{resources}"])


@router.get("/api/{resources}", response_model=list[{Resource}Response])
def list_{resources}(db: Session = Depends(get_db)):
    items = db.query({Resource}).order_by({Resource}.created_at.desc()).all()
    return items


@router.post("/api/{resources}", response_model={Resource}Response, status_code=201)
def create_{resource}(payload: {Resource}Create, db: Session = Depends(get_db)):
    item = {Resource}(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/api/{resources}/{{{resource}_id}}", response_model={Resource}Response)
def get_{resource}({resource}_id: str, db: Session = Depends(get_db)):
    item = db.query({Resource}).filter({Resource}.id == {resource}_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="{Resource} not found")
    return item


@router.put("/api/{resources}/{{{resource}_id}}", response_model={Resource}Response)
def update_{resource}({resource}_id: str, payload: {Resource}Update, db: Session = Depends(get_db)):
    item = db.query({Resource}).filter({Resource}.id == {resource}_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="{Resource} not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/api/{resources}/{{{resource}_id}}", status_code=204)
def delete_{resource}({resource}_id: str, db: Session = Depends(get_db)):
    item = db.query({Resource}).filter({Resource}.id == {resource}_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="{Resource} not found")
    db.delete(item)
    db.commit()
    return None
```

## Enregistrer le router

Dans `backend/main.py`, ajouter :
```python
from routers import {resources}
app.include_router({resources}.router)
```

## Règles NON-NÉGOCIABLES

1. `response_model` sur chaque endpoint (jamais retourner le ORM brut sans schema)
2. `status_code=201` sur POST, `status_code=204` sur DELETE
3. `model_dump(exclude_unset=True)` pour les updates partiels
4. `order_by(created_at.desc())` pour les listes
5. 404 avec `HTTPException` si ressource non trouvée
6. Tags = nom de la ressource pluriel

## Tests obligatoires

Créer `backend/tests/test_{resources}.py` → voir `templates/code/backend/test-backend/`

- `test_list_{resources}_empty` → GET → 200, `[]`
- `test_create_{resource}` → POST → 201
- `test_get_{resource}` → GET /{id} → 200
- `test_get_{resource}_not_found` → GET /bad-id → 404
- `test_update_{resource}` → PUT /{id} → 200
- `test_delete_{resource}` → DELETE /{id} → 204
