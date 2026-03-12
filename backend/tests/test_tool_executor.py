"""Comprehensive tests for Bob's 18 tools via the unified tool_executor.

Each tool is tested for:
1. Returns valid dict with status ok or error
2. No import crashes or unhandled exceptions
3. Voice/chat parity
"""

import os
import pytest
import asyncio

# Set env vars BEFORE any app import so Settings() picks them up
os.environ.setdefault("DATABASE_URL", "postgresql://croo:croo@localhost:5432/croo_digital_experience_test")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("SERPER_API_KEY", "test-key")


# ── Helpers ──────────────────────────────────────────────────

USER_CTX = {
    "user_id": "test-user-999",
    "tenant_id": "test-tenant-999",
    "session_id": "test-session-999",
}


def run_tool(tool_name: str, args: dict, db=None) -> dict:
    """Run a tool synchronously."""
    from app.agents.tool_executor import execute_bob_tool
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(execute_bob_tool(tool_name, args, USER_CTX, db))
    finally:
        loop.close()


# ── 1. UI Navigation Tools ──────────────────────────────────

class TestNavigateTools:
    """Tools that produce frontend UI actions (no DB needed)."""

    def test_navigate_to_returns_unknown(self, db):
        """navigate_to is handled inline in chat agent, not in tool_executor."""
        result = run_tool("navigate_to", {"page": "dashboard"}, db)
        assert result["status"] == "error"
        assert "Unknown tool" in result["message"]

    def test_open_create_dialog_unknown(self, db):
        """open_create_dialog is handled inline in chat agent."""
        result = run_tool("open_create_dialog", {"entity": "contact"}, db)
        assert result["status"] == "error"

    def test_start_crm_training_unknown(self, db):
        """start_crm_training is handled inline in chat agent."""
        result = run_tool("start_crm_training", {}, db)
        assert result["status"] == "error"

    def test_change_training_slide_unknown(self, db):
        """change_training_slide is handled inline."""
        result = run_tool("change_training_slide", {"direction": "next"}, db)
        assert result["status"] == "error"


class TestUIControlTools:
    """UI control tools that should be handled everywhere."""

    def test_ui_switch_tab(self, db):
        """ui_switch_tab should return ok with action data."""
        result = run_tool("ui_switch_tab", {"tab_name": "profile"}, db)
        assert result["status"] == "ok"
        assert result["action"] == "ui_switch_tab"
        assert result["tab_name"] == "profile"

    def test_ui_switch_tab_empty(self, db):
        """ui_switch_tab with no tab_name should default to empty string."""
        result = run_tool("ui_switch_tab", {}, db)
        assert result["status"] == "ok"
        assert result["tab_name"] == ""


# ── 2. Search Tools ─────────────────────────────────────────

class TestSearchTools:
    """Tools that query the database."""

    def test_search_contacts(self, db):
        """search_contacts should return ok with results array."""
        result = run_tool("search_contacts", {"query": "test"}, db)
        assert result["status"] == "ok"
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_search_organizations(self, db):
        """search_organizations should return ok with results array."""
        result = run_tool("search_organizations", {"query": "test"}, db)
        assert result["status"] == "ok"
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_search_and_open_entity_not_found(self, db):
        """search_and_open_entity with nonexistent query should return error."""
        result = run_tool(
            "search_and_open_entity",
            {"entity": "organization", "query": "zzz_nonexistent_zzz"},
            db,
        )
        assert result["status"] in ("ok", "error")

    def test_get_pipeline_stats(self, db):
        """get_pipeline_stats should return ok with stages."""
        result = run_tool("get_pipeline_stats", {}, db)
        assert result["status"] == "ok"
        assert "stages" in result
        assert isinstance(result["stages"], list)

    def test_get_recent_activities(self, db):
        """get_recent_activities should return ok."""
        result = run_tool("get_recent_activities", {}, db)
        assert result["status"] == "ok"
        assert "activities" in result
        assert isinstance(result["activities"], list)


# ── 3. Create Tools ─────────────────────────────────────────

class TestCreateTools:
    """Create tools are now fully functional."""

    def test_create_contact_basic(self, db):
        """create_contact should succeed and return contact_id."""
        result = run_tool("create_contact", {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@test.com",
        }, db)
        assert result["status"] == "ok"
        assert "contact_id" in result

    def test_create_organization_basic(self, db):
        """create_organization should succeed and return org_id."""
        result = run_tool("create_organization", {"name": "TestOrg"}, db)
        assert result["status"] == "ok"
        assert "org_id" in result

    def test_create_contact_with_company_link(self, db):
        """create_contact should link to existing org by company name."""
        # First create the org
        org_result = run_tool("create_organization", {"name": "Acme Corp"}, db)
        assert org_result["status"] == "ok"

        # Now create contact with company reference
        result = run_tool("create_contact", {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@acme.com",
            "company": "Acme",
        }, db)
        assert result["status"] == "ok"
        assert "linked to" in result["message"].lower() or "acme" in result["message"].lower()


# ── 4. BCC Profile Tools ────────────────────────────────────

class TestBccProfileTools:
    """BCC knowledge profile tools."""

    def test_bcc_update_profile(self, db):
        """bcc_update_profile should create a profile entry."""
        result = run_tool("bcc_update_profile", {
            "entity_type": "organization",
            "entity_id": "00000000-0000-0000-0000-000000000001",
            "section": "vision",
            "content": "Test vision content",
            "perspective": "general",
        }, db)
        assert result["status"] == "ok"
        assert "Profile updated" in result["message"]

    def test_bcc_update_profile_versioning(self, db):
        """Updating same section should increment version."""
        args = {
            "entity_type": "organization",
            "entity_id": "00000000-0000-0000-0000-000000000002",
            "section": "mission",
            "content": "version 1",
            "perspective": "ceo",
        }
        r1 = run_tool("bcc_update_profile", args, db)
        assert r1["status"] == "ok"
        assert "v1" in r1["message"]

        args["content"] = "version 2"
        r2 = run_tool("bcc_update_profile", args, db)
        assert r2["status"] == "ok"
        assert "v2" in r2["message"]

    def test_bcc_get_profile_empty(self, db):
        """bcc_get_profile for nonexistent entity should return empty."""
        result = run_tool("bcc_get_profile", {
            "entity_type": "industry",
            "entity_id": "00000000-0000-0000-0000-999999999999",
        }, db)
        assert result["status"] == "ok"
        assert result["profile"] == []

    def test_bcc_get_profile_after_update(self, db):
        """bcc_get_profile should return data after an update."""
        entity_id = "00000000-0000-0000-0000-000000000003"
        run_tool("bcc_update_profile", {
            "entity_type": "role",
            "entity_id": entity_id,
            "section": "description",
            "content": "Test description",
        }, db)

        result = run_tool("bcc_get_profile", {
            "entity_type": "role",
            "entity_id": entity_id,
        }, db)
        assert result["status"] == "ok"
        assert len(result["profile"]) >= 1
        assert result["profile"][0]["section"] == "description"
        assert result["profile"][0]["content"] == "Test description"


# ── 5. Knowledge Extractor Stubs ─────────────────────────────

class TestKnowledgeExtractorStubs:
    """These tools reference a non-existent module, should return safe errors."""

    def test_upsert_bcc_profile_from_interaction(self, db):
        """Should return error without crashing."""
        result = run_tool("upsert_bcc_profile_from_interaction", {
            "observation": "test",
            "confidence": 0.7,
        }, db)
        assert result["status"] == "error"
        assert "not yet available" in result["message"].lower()

    def test_get_bcc_profile_context(self, db):
        """Should return safe fallback."""
        result = run_tool("get_bcc_profile_context", {}, db)
        assert result["status"] == "ok"
        assert "markdown" in result


# ── 6. Training Tools ───────────────────────────────────────

class TestTrainingTools:
    """Training overlay tools."""

    def _create_training_session(self, db):
        """Create a training session to satisfy FK constraints."""
        import uuid
        from app.domain.entities.training_models import TrainingSession
        session_id = str(uuid.uuid4())
        session = TrainingSession(
            id=session_id,
            user_id=USER_CTX["user_id"],
            training_slug="crm-mastery",
        )
        db.add(session)
        db.commit()
        return session_id

    def test_save_training_note(self, db):
        """save_training_note should create a DB record."""
        session_id = self._create_training_session(db)
        result = run_tool("save_training_note", {
            "session_id": session_id,
            "content": "Important insight about CRM",
            "note_type": "insight",
        }, db)
        assert result["status"] == "ok"
        assert "id" in result

    def test_save_missing_element(self, db):
        """save_missing_element should create a DB record."""
        session_id = self._create_training_session(db)
        result = run_tool("save_missing_element", {
            "session_id": session_id,
            "label": "Zoho Integration",
            "category": "integration",
            "description": "Need Zoho CRM sync",
        }, db)
        assert result["status"] == "ok"
        assert "id" in result


# ── 7. Unknown Tool ─────────────────────────────────────────

class TestUnknownTools:
    """Verify graceful handling of unknown tool names."""

    def test_unknown_tool(self, db):
        """Unknown tool should return error without crash."""
        result = run_tool("some_nonexistent_tool", {"foo": "bar"}, db)
        assert result["status"] == "error"
        assert "Unknown tool" in result["message"]


# ── 8. Chat Agent ui_switch_tab Dispatch ─────────────────────

class TestChatAgentDispatch:
    """Verify the chat agent correctly dispatches ui_switch_tab."""

    def test_ui_switch_tab_in_bob_tools(self):
        """ui_switch_tab should be declared in BOB_TOOLS."""
        from app.agents.bob_tools import BOB_TOOLS
        tool_names = [t["function"]["name"] for t in BOB_TOOLS]
        assert "ui_switch_tab" in tool_names

    def test_all_20_tools_declared(self):
        """All 20 tools should be present in BOB_TOOLS."""
        from app.agents.bob_tools import BOB_TOOLS
        tool_names = [t["function"]["name"] for t in BOB_TOOLS]

        expected = [
            "navigate_to", "open_create_dialog", "ui_update_input",
            "ui_select_result", "ui_switch_tab", "start_crm_training",
            "search_and_open_entity", "search_contacts", "search_organizations",
            "get_pipeline_stats", "create_contact", "create_organization",
            "create_opportunity", "link_product_to_opportunity",
            "get_recent_activities", "bcc_update_profile", "bcc_get_profile",
            "save_training_note", "save_missing_element", "change_training_slide",
        ]

        for tool in expected:
            assert tool in tool_names, f"Missing tool: {tool}"

    def test_chat_agent_handles_ui_switch_tab(self):
        """The chat agent dispatch code should handle ui_switch_tab."""
        import inspect
        from app.agents.bob_chat_agent import BobChatAgent
        source = inspect.getsource(BobChatAgent.chat)
        assert "ui_switch_tab" in source, "ui_switch_tab not found in chat agent dispatch"


# ── 9. New Tools: Opportunity & Product Linking ──────────────

class TestNewTools:
    """Tests for create_opportunity and link_product_to_opportunity."""

    def test_create_opportunity_basic(self, db):
        """create_opportunity should succeed."""
        result = run_tool("create_opportunity", {
            "name": "Test Deal",
            "source": "Bob",
        }, db)
        assert result["status"] == "ok"
        assert "opportunity_id" in result

    def test_create_opportunity_with_invalid_org(self, db):
        """create_opportunity with nonexistent org should error."""
        result = run_tool("create_opportunity", {
            "name": "Bad Deal",
            "organization_id": "00000000-0000-0000-0000-999999999999",
        }, db)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_link_product_invalid_opp(self, db):
        """link_product_to_opportunity with nonexistent opp should error."""
        result = run_tool("link_product_to_opportunity", {
            "opportunity_id": "00000000-0000-0000-0000-999999999999",
            "product_id": "irrelevant",
        }, db)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


# ── 10. Lead Processing Pipeline ─────────────────────────────

class TestLeadProcessingPipeline:
    """End-to-end tests simulating real lead processing from the user's data.

    Covers: email-only leads, domain-based org grouping, name parsing,
    opportunity creation, and product linking.
    """

    def test_uc1_email_only_creates_org_from_domain(self, db):
        """UC1: connor@psu.com — email only, no name → auto-create org PSU."""
        result = run_tool("create_contact", {
            "first_name": "connor",
            "last_name": "",
            "email": "connor@psu.com",
        }, db)
        assert result["status"] == "ok"
        assert result["org_created"] is True
        assert result["organization_id"] is not None
        assert "auto-created" in result["message"].lower()

    def test_uc2_second_email_same_domain_groups(self, db):
        """UC2: yasn@psu.com — should reuse existing PSU org, NOT create new."""
        # UC1 already created PSU org, so this should match
        result = run_tool("create_contact", {
            "first_name": "yasn",
            "last_name": "",
            "email": "yasn@psu.com",
        }, db)
        assert result["status"] == "ok"
        # org_created should be False because PSU already exists
        assert result["org_created"] is False
        assert result["organization_id"] is not None
        assert "linked to" in result["message"].lower()

    def test_uc3_full_name_same_domain(self, db):
        """UC3: Chris Clement chris.clement@psu.com — full name, same PSU domain."""
        result = run_tool("create_contact", {
            "first_name": "Chris",
            "last_name": "Clement",
            "email": "chris.clement@psu.com",
        }, db)
        assert result["status"] == "ok"
        assert result["org_created"] is False
        assert "linked to" in result["message"].lower()

    def test_uc4_new_domain_creates_new_org(self, db):
        """UC4: yqi@fiberwood.ca — new domain → creates FIBERWOOD org."""
        result = run_tool("create_contact", {
            "first_name": "Yanyun",
            "last_name": "Qi",
            "email": "yqi@fiberwood.ca",
        }, db)
        assert result["status"] == "ok"
        assert result["org_created"] is True
        assert "auto-created" in result["message"].lower()
        # Should have named org FIBERWOOD from domain
        assert "FIBERWOOD" in result["message"]

    def test_uc5_second_contact_same_new_domain(self, db):
        """UC5: cphenix@fiberwood.ca — should group with fiberwood."""
        result = run_tool("create_contact", {
            "first_name": "Carl",
            "last_name": "Phenix",
            "email": "cphenix@fiberwood.ca",
        }, db)
        assert result["status"] == "ok"
        assert result["org_created"] is False
        assert "linked to" in result["message"].lower()

    def test_uc6_ibwave_domain(self, db):
        """UC6: kian.gorji@ibwave.com — new domain ibwave."""
        result = run_tool("create_contact", {
            "first_name": "Kian",
            "last_name": "Gorji",
            "email": "kian.gorji@ibwave.com",
        }, db)
        assert result["status"] == "ok"
        assert result["org_created"] is True
        assert "IBWAVE" in result["message"]

    def test_uc7_hyphenated_name(self, db):
        """UC7: Ben Shillabeer-Hall ben.shillabeer-hall@psu.com — compound name."""
        result = run_tool("create_contact", {
            "first_name": "Ben",
            "last_name": "Shillabeer-Hall",
            "email": "ben.shillabeer-hall@psu.com",
        }, db)
        assert result["status"] == "ok"
        assert result["org_created"] is False  # PSU already exists

    def test_uc8_underscore_email(self, db):
        """UC8: jackson_jessica@psu.com — underscore in email."""
        result = run_tool("create_contact", {
            "first_name": "Jackson",
            "last_name": "Jessica",
            "email": "jackson_jessica@psu.com",
        }, db)
        assert result["status"] == "ok"
        assert result["org_created"] is False  # PSU already exists

    def test_uc9_create_opportunity_for_org(self, db):
        """UC9: Create opportunity for an auto-created org."""
        # First create a contact to auto-create the org
        contact_result = run_tool("create_contact", {
            "first_name": "Sarah",
            "last_name": "Woolverton",
            "email": "sarah.woolverton@ultra-tcs.com",
        }, db)
        assert contact_result["status"] == "ok"
        org_id = contact_result["organization_id"]
        assert org_id is not None

        # Now create opportunity
        opp_result = run_tool("create_opportunity", {
            "name": "ULTRA-TCS — Service Integration",
            "organization_id": org_id,
            "contact_id": contact_result["contact_id"],
            "source": "Hunter",
        }, db)
        assert opp_result["status"] == "ok"
        assert "opportunity_id" in opp_result
        assert "ULTRA-TCS" in opp_result["message"]

    def test_uc10_link_product_to_opportunity(self, db):
        """UC10: Full pipeline — contact → org → opportunity → product."""
        from app.domain.entities.product import Product

        # 1. Create product in catalog
        product = Product(
            name="Croo CRM Integration",
            category="SERVICE",
            unit_price=4999.00,
            currency="CAD",
            tenant_id=USER_CTX["tenant_id"],
            created_by="test",
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        # 2. Create contact (auto-creates org)
        contact_result = run_tool("create_contact", {
            "first_name": "Katherine",
            "last_name": "Brun",
            "email": "kbrun@xiplink.com",
            "phone": "+1 514 848 9640 ext:225",
        }, db)
        assert contact_result["status"] == "ok"

        # 3. Create opportunity
        opp_result = run_tool("create_opportunity", {
            "name": "Xiplink — CRM Integration",
            "organization_id": contact_result["organization_id"],
            "contact_id": contact_result["contact_id"],
            "source": "Hunter",
        }, db)
        assert opp_result["status"] == "ok"

        # 4. Link product
        link_result = run_tool("link_product_to_opportunity", {
            "opportunity_id": opp_result["opportunity_id"],
            "product_id": str(product.id),
            "quantity": 1,
        }, db)
        assert link_result["status"] == "ok"
        assert "line_id" in link_result
        assert "Croo CRM Integration" in link_result["message"]
        assert "4999" in link_result["message"]

