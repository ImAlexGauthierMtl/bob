# Template: Schemas Pydantic (Create / Update / Response)

> Recette pour créer les schemas d'Input/Output d'une ressource.
> **Zéro décision** : 4 classes à créer, toujours le même pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Account` |
| `FIELDS` | Champs du modèle SQLAlchemy | copier du modèle |
| `ENUMS` | Enums importés | `AccountStatus` |

## Fichier à créer

`backend/core/{domain}/schemas.py`

## 4 classes à produire (dans cet ordre)

### 1. `{Resource}Base` — champs communs

```python
class {Resource}Base(BaseModel):
    """Champs communs Create + Response."""
    name: str                                    # champs obligatoires
    description: str = ""                        # champs optionnels avec défaut
    status: {Resource}Status = {Resource}Status.ACTIVE
    parent_id: Optional[str] = None              # FK optionnelle
```

**Règle** : inclure TOUS les champs sauf `id`, `created_at`, `updated_at`, et les champs auto-calculés.

### 2. `{Resource}Create` — hérite de Base (rien à ajouter en général)

```python
class {Resource}Create({Resource}Base):
    pass
```

### 3. `{Resource}Update` — tous les champs Optional

```python
class {Resource}Update(BaseModel):
    """Tous les champs optionnels pour update partiel."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[{Resource}Status] = None
    parent_id: Optional[str] = None
    # ... CHAQUE champ de Base, mais Optional[type] = None
```

**Règle** : hérite de `BaseModel` (PAS de `{Resource}Base`), car tous les champs doivent être Optional.

### 4. `{Resource}Response` — hérite de Base + ajoute id, timestamps

```python
class {Resource}Response({Resource}Base):
    """Format de sortie API."""
    id: str
    # Champs enrichis (noms résolus depuis FK)
    parent_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

## Imports requis

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from core.{domain}.models import {Resource}Status  # si enum
```

## Règles NON-NÉGOCIABLES

1. `model_config = {"from_attributes": True}` sur Response (permet la conversion ORM → Pydantic)
2. `Update` hérite de `BaseModel` (pas de Base) — tous Optional
3. `Create` hérite de `Base` — pass suffit en général
4. Ajouter les noms résolus dans Response (`account_name`, `owner_name`, etc.)
5. Pas de `id` dans Base ni Create (auto-généré)

## Après création

1. Ajouter les re-exports dans `backend/schemas.py`
2. Créer le router → voir `templates/code/backend/router-crud/`
