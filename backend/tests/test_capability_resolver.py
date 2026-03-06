"""Tests for CapabilityResolver — unit tests with direct DB access."""

import pytest
from app.application.services.capability_resolver import CapabilityResolver
from app.domain.entities.capability import CapabilityDefinition, UserCapability, DeptCapability
from app.domain.entities.department import Department, UserDepartment
from app.domain.entities.user import User


class TestCapabilityResolver:
    """Test the cascade resolution logic."""

    def test_system_capability_always_granted(self, db):
        """Default-enabled capabilities should be granted to any user."""
        resolver = CapabilityResolver(db)
        # Find a system default_enabled capability
        cap = db.query(CapabilityDefinition).filter(
            CapabilityDefinition.default_enabled == True,
        ).first()
        if cap:
            # Create a temp user for testing
            user = db.query(User).first()
            if user:
                result = resolver.can(user.id, cap.code, user.tenant_id)
                assert result is True

    def test_user_override_revokes_capability(self, db):
        """A user override with granted=False should revoke even a default-enabled capability."""
        resolver = CapabilityResolver(db)
        cap = db.query(CapabilityDefinition).filter(
            CapabilityDefinition.default_enabled == True,
        ).first()
        user = db.query(User).first()
        if cap and user:
            # Add user override revoking this capability
            uc = UserCapability(
                user_id=user.id,
                capability_id=cap.id,
                granted=False,
                granted_by="test",
                tenant_id=user.tenant_id,
            )
            db.add(uc)
            db.commit()

            result = resolver.can(user.id, cap.code, user.tenant_id)
            assert result is False

            # Cleanup
            db.delete(uc)
            db.commit()

    def test_nonexistent_capability_denied(self, db):
        """Non-existent capability codes should return False."""
        resolver = CapabilityResolver(db)
        user = db.query(User).first()
        if user:
            result = resolver.can(user.id, "totally.fake.capability", user.tenant_id)
            assert result is False

    def test_agent_mode_suggest_for_low_trust(self, db):
        """Users with trust_score < 0.3 should get 'suggest' mode."""
        user = db.query(User).first()
        if user:
            resolver = CapabilityResolver(db)
            old_score = user.trust_score
            user.trust_score = 0.1
            db.commit()

            mode = resolver.get_agent_mode(user)
            assert mode == "suggest"

            user.trust_score = old_score
            db.commit()

    def test_agent_mode_approval_for_mid_trust(self, db):
        """Users with trust_score 0.3-0.6 should get 'approval' mode."""
        user = db.query(User).first()
        if user:
            resolver = CapabilityResolver(db)
            old_score = user.trust_score
            user.trust_score = 0.5
            db.commit()

            mode = resolver.get_agent_mode(user)
            assert mode == "approval"

            user.trust_score = old_score
            db.commit()

    def test_agent_mode_auto_for_high_trust(self, db):
        """Users with trust_score > 0.6 should get 'auto' mode."""
        user = db.query(User).first()
        if user:
            resolver = CapabilityResolver(db)
            old_score = user.trust_score
            user.trust_score = 0.8
            db.commit()

            mode = resolver.get_agent_mode(user)
            assert mode == "auto"

            user.trust_score = old_score
            db.commit()

    def test_get_all_capabilities(self, db):
        """get_all_capabilities should return a list of dicts with required fields."""
        user = db.query(User).first()
        if user:
            resolver = CapabilityResolver(db)
            caps = resolver.get_all_capabilities(user.id, user.tenant_id)
            assert isinstance(caps, list)
            if len(caps) > 0:
                cap = caps[0]
                assert "code" in cap
                assert "name" in cap
                assert "scope" in cap
                assert "granted" in cap
                assert "source" in cap
