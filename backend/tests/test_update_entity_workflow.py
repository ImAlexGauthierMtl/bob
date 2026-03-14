"""Tests for the update_entity workflow — fuzzy resolve + disambiguation.

Covers:
1. Single match → auto-update
2. Multiple matches → disambiguation list (paused workflow)
3. No matches → error message
4. Full flow: multiple → pick → update applied
5. Field/value normalization (FR aliases)
"""

import os
import pytest

# Set env vars BEFORE any app import
os.environ.setdefault("DATABASE_URL", "postgresql://croo:croo@localhost:5432/croo_digital_experience_test")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("SERPER_API_KEY", "test-key")

from dataclasses import dataclass, field
from typing import Optional

from app.agents.workflow_engine import (
    WorkflowContext,
    WorkflowResult,
    update_entity_flow,
    resume_update_entity_pick,
    _normalize_field,
    _normalize_value,
)
from app.agents.intent_classifier import ExtractedEntities


TENANT = "test-tenant-update"
USER_ID = "test-user-update"
USER_EMAIL = "test@update.com"


def _make_ctx(db, entities, user_message="", state=None, session_messages=None):
    """Build a WorkflowContext for testing."""
    return WorkflowContext(
        db=db,
        tenant_id=TENANT,
        user_id=USER_ID,
        user_email=USER_EMAIL,
        entities=entities,
        user_message=user_message,
        state=state or {},
        session_messages=session_messages or [],
    )


def _create_org(db, name, status="PROSPECT"):
    """Helper — insert an org into the DB."""
    from app.domain.entities.organization import Organization
    org = Organization(
        name=name,
        status=status,
        tenant_id=TENANT,
        created_by=USER_EMAIL,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


# ── Normalization unit tests ─────────────────────────────────

class TestFieldNormalization:
    def test_french_alias(self):
        assert _normalize_field("statut") == "status"
        assert _normalize_field("industrie") == "industry"
        assert _normalize_field("téléphone") == "phone"

    def test_passthrough(self):
        assert _normalize_field("status") == "status"
        assert _normalize_field("industry") == "industry"

    def test_case_insensitive(self):
        assert _normalize_field("Statut") == "status"
        assert _normalize_field("INDUSTRIE") == "industry"


class TestValueNormalization:
    def test_french_status(self):
        assert _normalize_value("status", "client") == "CUSTOMER"
        assert _normalize_value("status", "actif") == "ACTIVE"

    def test_unknown_status_uppercased(self):
        assert _normalize_value("status", "new_custom") == "NEW_CUSTOM"

    def test_non_enum_passthrough(self):
        assert _normalize_value("industry", "Technology") == "Technology"


# ── Workflow integration tests ───────────────────────────────

class TestUpdateEntitySingleMatch:
    """1 match → auto-update without disambiguation."""

    def test_single_match_updates(self, db):
        org = _create_org(db, "ASQ Consultants", "PROSPECT")

        entities = ExtractedEntities(
            org_name="ASQ",
            entity_type="organization",
            update_field="status",
            update_value="client",
        )
        ctx = _make_ctx(db, entities)
        result = update_entity_flow(ctx)

        assert not result.paused
        assert "ASQ Consultants" in result.message
        assert "CUSTOMER" in result.message

        # Verify DB was updated
        from app.domain.entities.organization import Organization
        updated = db.query(Organization).filter(Organization.id == org.id).first()
        assert updated.status.value == "CUSTOMER"


class TestUpdateEntityMultipleMatches:
    """Multiple matches → pause with disambiguation list."""

    def test_multiple_matches_pauses(self, db):
        _create_org(db, "ASQ Consultants")
        _create_org(db, "ASQ Solutions")

        entities = ExtractedEntities(
            org_name="ASQ",
            entity_type="organization",
            update_field="status",
            update_value="client",
        )
        ctx = _make_ctx(db, entities)
        result = update_entity_flow(ctx)

        assert result.paused
        assert result.resume_key == "update_entity_pick"
        assert "ASQ Consultants" in result.message
        assert "ASQ Solutions" in result.message
        assert "2" in result.message  # "2 résultat(s)"


class TestUpdateEntityNoMatch:
    """0 matches → error message."""

    def test_no_match_returns_error(self, db):
        entities = ExtractedEntities(
            org_name="ZZZZZ_NONEXISTENT",
            entity_type="organization",
            update_field="status",
            update_value="client",
        )
        ctx = _make_ctx(db, entities)
        result = update_entity_flow(ctx)

        assert not result.paused
        assert "Aucun" in result.message


class TestUpdateEntityDisambiguationPick:
    """Full flow: search → >1 → pick #1 → update applied."""

    def test_pick_and_update(self, db):
        org1 = _create_org(db, "Bell Canada")
        _create_org(db, "Bell Helicopter")

        # Step 1: initial search triggers pause
        entities = ExtractedEntities(
            org_name="Bell",
            entity_type="organization",
            update_field="industry",
            update_value="Telecom",
        )
        ctx = _make_ctx(db, entities)
        result = update_entity_flow(ctx)

        assert result.paused
        assert result.resume_key == "update_entity_pick"

        # Step 2: user picks #1
        ctx2 = _make_ctx(db, entities, user_message="1", state=result.state)
        result2 = resume_update_entity_pick(ctx2)

        assert not result2.paused
        assert "Bell Canada" in result2.message
        assert "Telecom" in result2.message

        # Verify DB
        from app.domain.entities.organization import Organization
        updated = db.query(Organization).filter(Organization.id == org1.id).first()
        assert updated.industry == "Telecom"


class TestUpdateEntityMissingField:
    """No update_field → helpful error."""

    def test_missing_field(self, db):
        _create_org(db, "TestMissing Corp")

        entities = ExtractedEntities(
            org_name="TestMissing",
            entity_type="organization",
            update_field=None,
            update_value="something",
        )
        ctx = _make_ctx(db, entities)
        result = update_entity_flow(ctx)

        assert not result.paused
        assert "modifier" in result.message.lower() or "status" in result.message.lower()


class TestUpdateEntityInvalidField:
    """Invalid field name → error with suggestions."""

    def test_invalid_field(self, db):
        _create_org(db, "ValidOrg Inc")

        entities = ExtractedEntities(
            org_name="ValidOrg",
            entity_type="organization",
            update_field="nonexistent_field",
            update_value="test",
        )
        ctx = _make_ctx(db, entities)
        result = update_entity_flow(ctx)

        assert not result.paused
        assert "n'existe pas" in result.message
