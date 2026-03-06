# Template: Tests Unitaires Backend (pytest)

> Recette pour créer des tests unitaires avec fixtures, mocking, et database in-memory.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Client` |
| `resource` | Nom (snake_case) | `client` |

## Fichiers à créer

### 1. `tests/fixtures/database.py` — Fixtures DB

```python
"""Database fixtures for tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.base import Base
from app.domain.entities.{resource} import {Resource}


@pytest.fixture
def db_session():
    """Create a test database session (SQLite in-memory)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
```

### 2. `tests/unit/test_{resource}_repository.py`

```python
"""Tests unitaires pour {Resource}Repository."""

import pytest
from app.domain.entities.{resource} import {Resource}
from app.infrastructure.persistence.{resource}_repository import {Resource}Repository
from tests.fixtures.database import db_session


class TestCreate:
    def test_create_{resource}(self, db_session):
        repo = {Resource}Repository(db_session)
        entity = {Resource}(name="Test {Resource}")
        result = repo.create(entity)

        assert result.id is not None
        assert result.name == "Test {Resource}"
        assert result.is_deleted is False
        assert result.version == 1

    def test_create_{resource}_with_all_fields(self, db_session):
        repo = {Resource}Repository(db_session)
        entity = {Resource}(
            name="Full {Resource}",
            # description="Description complète",
            created_by="test-user"
        )
        result = repo.create(entity)
        assert result.name == "Full {Resource}"
        assert result.created_by == "test-user"


class TestGetById:
    def test_get_existing_{resource}(self, db_session):
        repo = {Resource}Repository(db_session)
        created = repo.create({Resource}(name="Test"))
        result = repo.get_by_id(created.id)
        assert result is not None
        assert result.id == created.id

    def test_get_nonexistent_{resource}(self, db_session):
        repo = {Resource}Repository(db_session)
        result = repo.get_by_id("nonexistent-id")
        assert result is None

    def test_get_deleted_{resource}_returns_none(self, db_session):
        repo = {Resource}Repository(db_session)
        created = repo.create({Resource}(name="Test"))
        repo.delete(created, deleted_by="test")
        result = repo.get_by_id(created.id)
        assert result is None


class TestGetAll:
    def test_list_empty(self, db_session):
        repo = {Resource}Repository(db_session)
        result = repo.get_all()
        assert result == []

    def test_list_multiple(self, db_session):
        repo = {Resource}Repository(db_session)
        repo.create({Resource}(name="A"))
        repo.create({Resource}(name="B"))
        result = repo.get_all()
        assert len(result) == 2

    def test_list_excludes_deleted(self, db_session):
        repo = {Resource}Repository(db_session)
        a = repo.create({Resource}(name="Active"))
        d = repo.create({Resource}(name="Deleted"))
        repo.delete(d, deleted_by="test")
        result = repo.get_all()
        assert len(result) == 1
        assert result[0].id == a.id

    def test_list_with_pagination(self, db_session):
        repo = {Resource}Repository(db_session)
        for i in range(5):
            repo.create({Resource}(name=f"Item {i}"))
        result = repo.get_all(skip=2, limit=2)
        assert len(result) == 2


class TestUpdate:
    def test_update_{resource}(self, db_session):
        repo = {Resource}Repository(db_session)
        created = repo.create({Resource}(name="Original"))
        created.name = "Updated"
        result = repo.update(created)
        assert result.name == "Updated"
        assert result.version == 2


class TestDelete:
    def test_soft_delete_{resource}(self, db_session):
        repo = {Resource}Repository(db_session)
        created = repo.create({Resource}(name="To Delete"))
        result = repo.delete(created, deleted_by="test-user", reason="Test deletion")
        assert result.is_deleted is True
        assert result.deleted_by == "test-user"
        assert result.deleted_reason == "Test deletion"
        assert result.deleted_at is not None
```

### 3. `tests/unit/test_{resource}_use_cases.py`

```python
"""Tests unitaires pour les use cases {Resource}."""

import pytest
from app.domain.entities.{resource} import {Resource}
from app.application.use_cases.create_{resource} import Create{Resource}UseCase
from app.application.use_cases.list_{resources} import List{Resources}UseCase
from app.application.use_cases.get_{resource}_by_id import Get{Resource}ByIdUseCase
from app.application.use_cases.update_{resource} import Update{Resource}UseCase
from app.application.use_cases.delete_{resource} import Delete{Resource}UseCase
from tests.fixtures.database import db_session


class TestCreate{Resource}UseCase:
    def test_create_success(self, db_session):
        uc = Create{Resource}UseCase(db_session)
        result = uc.execute(name="New {Resource}")
        assert result.id is not None
        assert result.name == "New {Resource}"


class TestList{Resources}UseCase:
    def test_list_empty(self, db_session):
        uc = List{Resources}UseCase(db_session)
        result = uc.execute()
        assert result == []

    def test_list_with_items(self, db_session):
        Create{Resource}UseCase(db_session).execute(name="A")
        Create{Resource}UseCase(db_session).execute(name="B")
        result = List{Resources}UseCase(db_session).execute()
        assert len(result) == 2


class TestGet{Resource}ByIdUseCase:
    def test_get_existing(self, db_session):
        created = Create{Resource}UseCase(db_session).execute(name="Test")
        result = Get{Resource}ByIdUseCase(db_session).execute(created.id)
        assert result is not None

    def test_get_nonexistent(self, db_session):
        result = Get{Resource}ByIdUseCase(db_session).execute("bad-id")
        assert result is None


class TestDelete{Resource}UseCase:
    def test_delete_existing(self, db_session):
        created = Create{Resource}UseCase(db_session).execute(name="Test")
        result = Delete{Resource}UseCase(db_session).execute(created.id, deleted_by="test")
        assert result is True

    def test_delete_nonexistent(self, db_session):
        result = Delete{Resource}UseCase(db_session).execute("bad-id", deleted_by="test")
        assert result is False
```

## Règles NON-NÉGOCIABLES

1. SQLite in-memory pour les tests — jamais de connexion à une vraie DB
2. `create_all()` dans le fixture, `drop_all()` dans le cleanup
3. Chaque test est isolé — pas d'état partagé entre tests
4. Tester les cas positifs ET négatifs (not found, deleted, etc.)
5. Grouper par classe : `TestCreate`, `TestGetById`, etc.
6. Exécuter avec `pytest tests/unit/ -v --tb=short`
