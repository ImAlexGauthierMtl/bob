# Template: Modèle SQLAlchemy

> Recette pour créer un nouveau modèle de données.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom de la ressource (PascalCase) | `Account` |
| `TABLE` | Nom de la table (snake_case, pluriel) | `accounts` |
| `FIELDS` | Liste des champs avec types | voir ci-dessous |
| `ENUMS` | Enums associés (optionnel) | `AccountStatus` |
| `RELATIONS` | Relations (optionnel) | `contacts`, `deals` |

## Fichier à créer

`backend/core/{domain}/models.py`

Si le fichier existe déjà, ajouter la classe à la fin.

## Code exact à produire

### 1. Enum (si statut ou type)

```python
class {Resource}Status(str, enum.Enum):
    """Statuts possibles pour {Resource}."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    # ... ajouter les valeurs métier
```

### 2. Modèle

```python
class {Resource}(Base):
    __tablename__ = "{table}"

    # PK — toujours string UUID
    id = Column(String, primary_key=True, default=generate_uuid)

    # Champs métier — adapter selon les FIELDS
    name = Column(String(255), nullable=False)
    # ... un Column par champ

    # Statut (si enum)
    status = Column(SAEnum({Resource}Status), default={Resource}Status.ACTIVE)

    # FK (si relation parent)
    # parent_id = Column(String, ForeignKey("{parent_table}.id"), nullable=True)

    # Timestamps — TOUJOURS présents
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relations — TOUJOURS après les colonnes
    # children = relationship("{Child}", back_populates="{resource}")
```

## Imports requis

```python
import enum

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Date, Float,
    ForeignKey, Enum as SAEnum, Integer,
)
from sqlalchemy.orm import relationship

from database import Base
from core.shared import generate_uuid, utc_now
```

## Règles NON-NÉGOCIABLES

1. PK = `String` + `generate_uuid` (jamais Integer autoincrement)
2. `created_at` et `updated_at` TOUJOURS présents
3. Enums = `str, enum.Enum` (jamais plain string)
4. Relations déclarées avec `back_populates` (pas `backref`)
5. `nullable=False` seulement pour les champs obligatoires métier
6. Défaut = string vide `""` pour les champs texte optionnels (pas None)

## Après création

1. Ajouter le re-export dans `backend/models.py`
2. Créer une migration Alembic
3. Créer les schemas Pydantic → voir `templates/code/backend/schemas-pydantic/`
