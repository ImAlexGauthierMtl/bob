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
from app.domain.entities import kb_article, tenant  # noqa: F401
from app.domain.entities import training_models, bcc_entities  # noqa: F401
from app.domain.entities import usage_transaction  # noqa: F401
from app.domain.entities import product, opportunity_product  # noqa: F401
from app.domain.entities import enrichment_run  # noqa: F401
from app.domain.entities import ms365_connection, synced_email, synced_event  # noqa: F401

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
def auth_headers(client, db):
    """Register a test user and return auth headers."""
    client.post("/api/v1/auth/register", json={
        "email": "test@crootest.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
    })

    # Give the user 'activity' permissions dynamically in test DB
    from app.domain.entities.user import User
    from app.domain.entities.role import Role, Permission, UserRole, RolePermission
    user = db.query(User).filter_by(email="test@crootest.com").first()
    if user:
        role = db.query(Role).filter_by(name="test_activity_admin").first()
        if not role:
            role = Role(name="test_activity_admin", description="Test Role", tenant_id="default")
            db.add(role)
            db.commit()
            db.refresh(role)
            
            p1 = db.query(Permission).filter_by(resource="activity", action="write").first()
            if not p1:
                p1 = Permission(resource="activity", action="write")
                db.add(p1)
                db.commit()
                db.refresh(p1)
                
            p2 = db.query(Permission).filter_by(resource="activity", action="delete").first()
            if not p2:
                p2 = Permission(resource="activity", action="delete")
                db.add(p2)
                db.commit()
                db.refresh(p2)
                
            db.add(RolePermission(role_id=role.id, permission_id=p1.id))
            db.add(RolePermission(role_id=role.id, permission_id=p2.id))
            db.commit()
            
        # Ensure user has the role
        user_role = db.query(UserRole).filter_by(user_id=user.id, role_id=role.id).first()
        if not user_role:
            db.add(UserRole(user_id=user.id, role_id=role.id))
            db.commit()

    response = client.post("/api/v1/auth/login", json={
        "email": "test@crootest.com",
        "password": "TestPass123!",
    })
    token = response.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}
