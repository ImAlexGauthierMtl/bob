# Template: Entité de Domaine (Clean Architecture)

> Recette pour créer une entité de domaine avec audit et soft delete.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Client` |
| `TABLE` | Nom de la table (snake_case, pluriel) | `clients` |
| `FIELDS` | Champs métier | voir ci-dessous |

## Fichier à créer

`app/domain/entities/{resource}.py`

## Code exact

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, Float, ForeignKey, func
from sqlalchemy.orm import relationship
from shared.database.base import Base
import uuid


def generate_uuid() -> str:
    """Génère un UUID v4 en string."""
    return str(uuid.uuid4())


class {Resource}(Base):
    """Entité {Resource}."""
    __tablename__ = "{table}"

    # PK — toujours string UUID
    id = Column(String(36), primary_key=True, default=generate_uuid)

    # --- Champs métier --- adapter selon les FIELDS
    name = Column(String(255), nullable=False)
    # description = Column(Text, nullable=True)
    # email = Column(String(255), nullable=True)
    # phone = Column(String(50), nullable=True)
    # status = Column(String(50), default="active")
    # amount = Column(Float, nullable=True)

    # FK optionnelle (si relation parent)
    # parent_id = Column(String(36), ForeignKey("{parent_table}.id"), nullable=True)

    # --- Audit fields --- TOUJOURS présents
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    version = Column(Integer, default=1, nullable=False)

    # --- Soft delete fields --- TOUJOURS présents
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(String(100), nullable=True)
    deleted_reason = Column(Text, nullable=True)

    # --- Relations --- après les colonnes
    # children = relationship("{Child}", back_populates="{resource}")
```

## Règles NON-NÉGOCIABLES

1. PK = `String(36)` + `generate_uuid` (jamais Integer autoincrement)
2. Audit fields TOUJOURS : `created_at`, `updated_at`, `created_by`, `updated_by`, `version`
3. Soft delete TOUJOURS : `is_deleted`, `deleted_at`, `deleted_by`, `deleted_reason`
4. `is_deleted` indexé pour performance
5. Timestamps avec `timezone=True` et `server_default=func.now()`
6. Relations avec `back_populates` (pas `backref`)
7. Import depuis `shared.database.base.Base` (shared lib)

## Après création

1. Créer la migration Alembic → voir `templates/code/backend/alembic-migration/`
2. Créer le repository → voir `templates/code/backend/repository-pattern/`
3. Créer les use cases → voir `templates/code/backend/use-case/`
