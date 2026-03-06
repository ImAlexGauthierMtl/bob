# Template: Tests d'Intégration Backend

> Recette pour créer des tests d'intégration avec TestClient FastAPI.
> **Zéro décision** : suivre exactement ce pattern.

## Input requis

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `RESOURCE` | Nom (PascalCase) | `Client` |
| `resources` | Pluriel (snake_case) | `clients` |

## Fichier à créer

`tests/integration/endpoints/test_{resources}_endpoints.py`

## Code exact

```python
"""Tests d'intégration pour les endpoints {resources}."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.base import Base
from app.domain.entities.{resource} import {Resource}
from main import app
from app.infrastructure.database import get_db


# Override database dependency pour les tests
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    """Recreate tables before each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


class TestList{Resources}:
    def test_list_empty(self):
        response = client.get("/api/v1/{resources}")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_items(self):
        # Create test data
        client.post("/api/v1/{resources}", json={"name": "Test 1"})
        client.post("/api/v1/{resources}", json={"name": "Test 2"})
        response = client.get("/api/v1/{resources}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestCreate{Resource}:
    def test_create_success(self):
        response = client.post("/api/v1/{resources}", json={
            "name": "New {Resource}",
            # ... autres champs requis
        })
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New {Resource}"
        assert "id" in data
        assert "created_at" in data

    def test_create_missing_required_field(self):
        response = client.post("/api/v1/{resources}", json={})
        assert response.status_code == 422  # Validation error


class TestGet{Resource}:
    def test_get_existing(self):
        create_response = client.post("/api/v1/{resources}", json={"name": "Test"})
        item_id = create_response.json()["id"]
        response = client.get(f"/api/v1/{resources}/{item_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Test"

    def test_get_not_found(self):
        response = client.get("/api/v1/{resources}/nonexistent-id")
        assert response.status_code == 404


class TestUpdate{Resource}:
    def test_update_success(self):
        create_response = client.post("/api/v1/{resources}", json={"name": "Original"})
        item_id = create_response.json()["id"]
        response = client.put(f"/api/v1/{resources}/{item_id}", json={"name": "Updated"})
        assert response.status_code == 200
        assert response.json()["name"] == "Updated"

    def test_update_not_found(self):
        response = client.put("/api/v1/{resources}/nonexistent-id", json={"name": "Updated"})
        assert response.status_code == 404

    def test_partial_update(self):
        create_response = client.post("/api/v1/{resources}", json={"name": "Original"})
        item_id = create_response.json()["id"]
        response = client.put(f"/api/v1/{resources}/{item_id}", json={"name": "Partial"})
        assert response.status_code == 200


class TestDelete{Resource}:
    def test_delete_success(self):
        create_response = client.post("/api/v1/{resources}", json={"name": "To Delete"})
        item_id = create_response.json()["id"]
        response = client.delete(f"/api/v1/{resources}/{item_id}")
        assert response.status_code == 204

    def test_delete_not_found(self):
        response = client.delete("/api/v1/{resources}/nonexistent-id")
        assert response.status_code == 404

    def test_delete_then_get_returns_not_found(self):
        create_response = client.post("/api/v1/{resources}", json={"name": "To Delete"})
        item_id = create_response.json()["id"]
        client.delete(f"/api/v1/{resources}/{item_id}")
        response = client.get(f"/api/v1/{resources}/{item_id}")
        assert response.status_code == 404
```

## Règles NON-NÉGOCIABLES

1. `dependency_overrides` pour remplacer `get_db` par SQLite in-memory
2. `autouse=True` fixture pour recreer les tables avant chaque test
3. Tester status codes ET body
4. 10 tests minimum : list_empty, list_items, create, create_invalid, get, get_404, update, update_404, delete, delete_404
5. Grouper par endpoint : `TestList`, `TestCreate`, `TestGet`, `TestUpdate`, `TestDelete`
