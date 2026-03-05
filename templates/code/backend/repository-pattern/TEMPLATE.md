# Template: Repository Pattern (Persistence)

> Recette pour créer un repository d'accès aux données.
> **Zéro décision** : CRUD complet + filtres + soft delete.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Client` |
| `resource` | Nom (snake_case) | `client` |

## Fichier à créer

`app/infrastructure/persistence/{resource}_repository.py`

## Code exact

```python
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.domain.entities.{resource} import {Resource}


class {Resource}Repository:
    """Repository pour les opérations sur les {resources}."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, entity: {Resource}) -> {Resource}:
        """Crée un(e) {Resource}."""
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_by_id(self, {resource}_id: str) -> Optional[{Resource}]:
        """Récupère un(e) {Resource} par son ID."""
        return self.db.query({Resource}).filter(
            {Resource}.id == {resource}_id,
            {Resource}.is_deleted == False
        ).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[{Resource}]:
        """Récupère tous les {resources} avec pagination et recherche."""
        query = self.db.query({Resource}).filter(
            {Resource}.is_deleted == False
        )

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    {Resource}.name.ilike(search_filter),
                    # Ajouter d'autres champs de recherche ici
                )
            )

        return query.order_by(
            {Resource}.created_at.desc()
        ).offset(skip).limit(limit).all()

    def count(self, search: Optional[str] = None) -> int:
        """Compte le nombre total de {resources}."""
        query = self.db.query(func.count({Resource}.id)).filter(
            {Resource}.is_deleted == False
        )
        if search:
            search_filter = f"%{search}%"
            query = query.filter({Resource}.name.ilike(search_filter))
        return query.scalar() or 0

    def update(self, entity: {Resource}) -> {Resource}:
        """Met à jour un(e) {Resource}."""
        entity.version += 1
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: {Resource}, deleted_by: str, reason: Optional[str] = None) -> {Resource}:
        """Soft delete d'un(e) {Resource}."""
        from datetime import datetime
        entity.is_deleted = True
        entity.deleted_at = datetime.utcnow()
        entity.deleted_by = deleted_by
        entity.deleted_reason = reason
        entity.version += 1
        self.db.commit()
        self.db.refresh(entity)
        return entity
```

## Règles NON-NÉGOCIABLES

1. Toujours filter `is_deleted == False` dans les queries
2. `commit()` + `refresh()` après chaque écriture
3. Pagination avec `skip`/`limit` — jamais de `.all()` sans limit
4. Recherche avec `ilike` (case-insensitive)
5. Ordering par `created_at.desc()` par défaut
6. `version += 1` sur chaque update/delete
7. Soft delete par défaut — stocker `deleted_at`, `deleted_by`, `deleted_reason`
