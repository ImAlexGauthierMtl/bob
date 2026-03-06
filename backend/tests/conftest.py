"""Pytest configuration and fixtures for backend tests."""

import os
import pytest

# Set env vars BEFORE any app import so Settings() picks them up
os.environ["DATABASE_URL"] = "postgresql://croo:croo@localhost:5432/croo_digital_experience_test"
os.environ["GROQ_API_KEY"] = "test-key"
os.environ["SERPER_API_KEY"] = "test-key"

# Now force-reload settings with test DB
from app.config import settings
settings.database_url = os.environ["DATABASE_URL"]

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.entities.base import Base
from app.infrastructure.database import get_db
from main import app

# Import all entities so they register with Base.metadata
from app.domain.entities import user, organization, contact, opportunity, quote, activity  # noqa: F401
from app.domain.entities import department, capability, workflow, workflow_execution  # noqa: F401
from app.domain.entities import kb_article  # noqa: F401

# Create test engine pointing to test DB
test_engine = create_engine(settings.database_url)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create all tables on test DB (drop first for schema updates)
Base.metadata.drop_all(bind=test_engine)
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def db():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Register a test user and return auth headers."""
    client.post("/api/v1/auth/register", json={
        "email": "test@crootest.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
    })
    response = client.post("/api/v1/auth/login", json={
        "email": "test@crootest.com",
        "password": "TestPass123!",
    })
    token = response.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}
