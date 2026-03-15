"""Generic CRUD repository with tenant isolation — base for all backend-api repositories."""

from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session, selectinload, RelationshipProperty
from sqlalchemy import inspect as sa_inspect

from ...database.base import Base
from ...database.mixins import generate_uuid, utc_now
from ...utils.exceptions import NotFoundError

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Generic CRUD repository with tenant_id isolation and eager loading.

    Usage:
        class ContactRepository(BaseRepository[Contact]):
            model = Contact
            eager_relationships = ["organization", "activities"]
    """

    model: Type[T]
    eager_relationships: List[str] = []

    def __init__(self, db: Session):
        self.db = db

    def _apply_eager_loads(self, query):
        for rel_name in self.eager_relationships:
            mapper = sa_inspect(self.model)
            if rel_name in mapper.relationships:
                query = query.options(selectinload(getattr(self.model, rel_name)))
        return query

    def get_by_id(self, entity_id: str, tenant_id: str) -> T:
        query = self.db.query(self.model).filter(
            self.model.id == entity_id,
            self.model.tenant_id == tenant_id,
        )
        if hasattr(self.model, "is_deleted"):
            query = query.filter(self.model.is_deleted == False)  # noqa: E712
        query = self._apply_eager_loads(query)
        entity = query.first()
        if not entity:
            raise NotFoundError(self.model.__name__, entity_id)
        return entity

    def list_all(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[T]:
        query = self.db.query(self.model).filter(self.model.tenant_id == tenant_id)
        if hasattr(self.model, "is_deleted"):
            query = query.filter(self.model.is_deleted == False)  # noqa: E712
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        query = self._apply_eager_loads(query)
        if hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())
        return query.offset(skip).limit(limit).all()

    def count(self, tenant_id: str, filters: Optional[Dict[str, Any]] = None) -> int:
        query = self.db.query(self.model).filter(self.model.tenant_id == tenant_id)
        if hasattr(self.model, "is_deleted"):
            query = query.filter(self.model.is_deleted == False)  # noqa: E712
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.filter(getattr(self.model, key) == value)
        return query.count()

    def create(self, data: Dict[str, Any], tenant_id: str, user_id: Optional[str] = None) -> T:
        if "id" not in data:
            data["id"] = generate_uuid()
        data["tenant_id"] = tenant_id
        if user_id and hasattr(self.model, "created_by"):
            data["created_by"] = user_id
        entity = self.model(**data)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity_id: str, data: Dict[str, Any], tenant_id: str, user_id: Optional[str] = None) -> T:
        entity = self.get_by_id(entity_id, tenant_id)
        for key, value in data.items():
            if hasattr(entity, key) and value is not None:
                setattr(entity, key, value)
        if user_id and hasattr(entity, "updated_by"):
            entity.updated_by = user_id
        if hasattr(entity, "updated_at"):
            entity.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity_id: str, tenant_id: str, user_id: Optional[str] = None, soft: bool = True) -> bool:
        entity = self.get_by_id(entity_id, tenant_id)
        if soft and hasattr(entity, "is_deleted"):
            entity.is_deleted = True
            entity.deleted_at = utc_now()
            if user_id:
                entity.deleted_by = user_id
            self.db.commit()
        else:
            self.db.delete(entity)
            self.db.commit()
        return True
