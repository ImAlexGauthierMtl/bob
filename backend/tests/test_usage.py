"""Tests for Usage Transaction Ledger API and tracking."""


class TestUsageCRUD:
    """Test Usage API endpoints."""

    def test_list_usage_empty(self, client, auth_headers):
        """GET /api/v1/usage returns empty list for a new tenant."""
        response = client.get("/api/v1/usage", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_usage_after_tracking(self, client, auth_headers, db):
        """After inserting a transaction via repo, it appears via API."""
        from app.domain.entities.usage_transaction import (
            UsageTransaction, ServiceType, BillingCategory, TriggerSource,
        )
        from app.infrastructure.persistence.usage_repository import UsageRepository

        # Find test user's tenant_id
        me = client.get("/api/v1/auth/me", headers=auth_headers)
        tenant_id = me.json().get("tenant_id", "default")

        repo = UsageRepository(db)
        txn = UsageTransaction(
            tenant_id=tenant_id,
            user_id="test-user",
            service_type=ServiceType.LLM,
            provider="groq",
            model="qwen/qwen3-32b",
            is_billable=True,
            billing_category=BillingCategory.AI_USAGE,
            trigger_source=TriggerSource.BOB_CHAT,
            input_tokens=100,
            output_tokens=50,
            cogs_amount=0.000058,
            cogs_currency="USD",
        )
        repo.create(txn)

        response = client.get("/api/v1/usage", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        found = [i for i in data["items"] if i["model"] == "qwen/qwen3-32b"]
        assert len(found) >= 1
        assert found[0]["service_type"] == "LLM"

    def test_usage_summary(self, client, auth_headers, db):
        """GET /api/v1/usage/summary returns aggregated data."""
        from app.domain.entities.usage_transaction import (
            UsageTransaction, ServiceType, BillingCategory, TriggerSource,
        )
        from app.infrastructure.persistence.usage_repository import UsageRepository

        me = client.get("/api/v1/auth/me", headers=auth_headers)
        tenant_id = me.json().get("tenant_id", "default")

        repo = UsageRepository(db)
        for i in range(3):
            txn = UsageTransaction(
                tenant_id=tenant_id,
                user_id="test-user",
                service_type=ServiceType.STT,
                provider="groq",
                model="whisper-large-v3-turbo",
                is_billable=True,
                billing_category=BillingCategory.VOICE,
                trigger_source=TriggerSource.BOB_VOICE,
                audio_seconds=5.0,
                cogs_amount=0.00005,
                cogs_currency="USD",
            )
            repo.create(txn)

        response = client.get("/api/v1/usage/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_transactions"] >= 3

    def test_usage_filter_by_service_type(self, client, auth_headers, db):
        """Usage list can be filtered by service_type."""
        response = client.get(
            "/api/v1/usage?service_type=STT",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["service_type"] == "STT"

    def test_rate_card_seed(self, db):
        """Rate cards are seeded correctly."""
        from app.infrastructure.seed_rate_cards import seed_rate_cards
        from app.domain.entities.usage_transaction import CostRateCard

        seed_rate_cards(db)

        cards = db.query(CostRateCard).all()
        assert len(cards) == 7  # 4 LLM (2 models × 2 unit types) + STT + TTS + Search

        # Check per-model rate for qwen/qwen3-32b
        groq_llm = db.query(CostRateCard).filter(
            CostRateCard.provider == "groq",
            CostRateCard.model == "qwen/qwen3-32b",
            CostRateCard.unit_type == "INPUT_TOKEN",
        ).first()
        assert groq_llm is not None
        assert abs(float(groq_llm.rate_per_unit) - 0.29 / 1_000_000) < 1e-12  # $0.29/1M tokens

    def test_usage_tracker_llm(self, db):
        """UsageTracker.track_llm persists a transaction."""
        from app.middleware.usage_tracker import UsageTracker
        from app.domain.entities.usage_transaction import UsageTransaction, TriggerSource
        from app.infrastructure.seed_rate_cards import seed_rate_cards

        # Ensure rate cards exist
        seed_rate_cards(db)

        tracker = UsageTracker(db)
        txn = tracker.track_llm(
            tenant_id="test-tenant",
            user_id="test-user",
            user_email="test@test.com",
            model="qwen/qwen3-32b",
            input_tokens=500,
            output_tokens=200,
            trigger_source=TriggerSource.BOB_CHAT,
            trigger_id="session-123",
            correlation_id="session-123",
        )

        assert txn.id is not None
        assert txn.service_type.value == "LLM"
        assert txn.input_tokens == 500
        assert txn.output_tokens == 200
        assert float(txn.cogs_amount) > 0

        # Verify it's in the DB
        found = db.query(UsageTransaction).filter(
            UsageTransaction.id == txn.id,
        ).first()
        assert found is not None

    def test_usage_tracker_stt(self, db):
        """UsageTracker.track_stt persists a transaction."""
        from app.middleware.usage_tracker import UsageTracker
        from app.infrastructure.seed_rate_cards import seed_rate_cards

        seed_rate_cards(db)

        tracker = UsageTracker(db)
        txn = tracker.track_stt(
            tenant_id="test-tenant",
            user_id="test-user",
            model="whisper-large-v3-turbo",
            audio_seconds=10.5,
            trigger_id="voice-session-1",
        )

        assert txn.id is not None
        assert txn.service_type.value == "STT"
        assert txn.audio_seconds == 10.5
        assert float(txn.cogs_amount) > 0

    def test_usage_tracker_tool(self, db):
        """UsageTracker.track_tool persists zero-cost transaction."""
        from app.middleware.usage_tracker import UsageTracker

        tracker = UsageTracker(db)
        txn = tracker.track_tool(
            tenant_id="test-tenant",
            user_id="test-user",
            tool_name="navigate_to",
        )

        assert txn.id is not None
        assert txn.service_type.value == "TOOL"
        assert txn.is_billable is False
        assert float(txn.cogs_amount) == 0
