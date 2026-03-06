# Template: Use Case (Clean Architecture)

> Recette pour créer un use case dans la couche application.
> **Zéro décision** : 1 classe par use case, injection du repository.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Client` |
| `ACTION` | Action du use case | `Create`, `List`, `GetById`, `Update`, `Delete` |

## Fichier à créer

`app/application/use_cases/{action}_{resource}.py`

## Code exact — CRUD complet (5 use cases)

### `create_{resource}.py`

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.entities.{resource_snake} import {Resource}
from app.infrastructure.persistence.{resource_snake}_repository import {Resource}Repository


class Create{Resource}UseCase:
    """Use case pour la création d'un(e) {Resource}."""

    def __init__(self, db: Session):
        self.repository = {Resource}Repository(db)

    def execute(self, **kwargs) -> {Resource}:
        """Crée un(e) nouveau/nouvelle {Resource}."""
        # Validation métier
        # ex: vérifier unicité, vérifier les contraintes métier

        entity = {Resource}(**kwargs)
        return self.repository.create(entity)
```

### `list_{resources}.py`

```python
from typing import List, Optional
from sqlalchemy.orm import Session
from app.domain.entities.{resource_snake} import {Resource}
from app.infrastructure.persistence.{resource_snake}_repository import {Resource}Repository


class List{Resources}UseCase:
    """Use case pour lister les {resources}."""

    def __init__(self, db: Session):
        self.repository = {Resource}Repository(db)

    def execute(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[{Resource}]:
        """Retourne la liste des {resources}."""
        return self.repository.get_all(skip=skip, limit=limit, search=search)
```

### `get_{resource}_by_id.py`

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.entities.{resource_snake} import {Resource}
from app.infrastructure.persistence.{resource_snake}_repository import {Resource}Repository


class Get{Resource}ByIdUseCase:
    """Use case pour récupérer un(e) {Resource} par ID."""

    def __init__(self, db: Session):
        self.repository = {Resource}Repository(db)

    def execute(self, {resource_snake}_id: str) -> Optional[{Resource}]:
        """Récupère un(e) {Resource} par son ID."""
        return self.repository.get_by_id({resource_snake}_id)
```

### `update_{resource}.py`

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.entities.{resource_snake} import {Resource}
from app.infrastructure.persistence.{resource_snake}_repository import {Resource}Repository


class Update{Resource}UseCase:
    """Use case pour mettre à jour un(e) {Resource}."""

    def __init__(self, db: Session):
        self.repository = {Resource}Repository(db)

    def execute(self, {resource_snake}_id: str, **kwargs) -> Optional[{Resource}]:
        """Met à jour un(e) {Resource}."""
        entity = self.repository.get_by_id({resource_snake}_id)
        if not entity:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(entity, key):
                setattr(entity, key, value)

        return self.repository.update(entity)
```

### `delete_{resource}.py`

```python
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.entities.{resource_snake} import {Resource}
from app.infrastructure.persistence.{resource_snake}_repository import {Resource}Repository


class Delete{Resource}UseCase:
    """Use case pour supprimer un(e) {Resource} (soft delete)."""

    def __init__(self, db: Session):
        self.repository = {Resource}Repository(db)

    def execute(self, {resource_snake}_id: str, deleted_by: str, reason: Optional[str] = None) -> bool:
        """Soft delete d'un(e) {Resource}."""
        entity = self.repository.get_by_id({resource_snake}_id)
        if not entity:
            return False

        self.repository.delete(entity, deleted_by=deleted_by, reason=reason)
        return True
```

## Règles NON-NÉGOCIABLES

1. 1 fichier = 1 use case = 1 classe = 1 méthode `execute()`
2. Le use case reçoit la `Session` DB et instancie le repository
3. Validation métier dans le use case, PAS dans le router
4. Jamais d'import de FastAPI dans un use case (couche application pure)
5. Retour : l'entité ou `None`/`bool` — jamais de HTTPException ici
6. Soft delete par défaut — jamais de hard delete sauf besoin explicite
