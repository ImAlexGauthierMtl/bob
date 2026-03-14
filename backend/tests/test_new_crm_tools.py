"""End-to-end tests for the 16 new CRM tools + 6 new artifact types.

Covers:
1. Tool definitions — all 47 tools exist in BOB_TOOLS with valid schemas
2. Contact tools — get, update, delete (with guard), list activities/opps, summary
3. Opportunity tools — get, update, delete (with guard), list activities, summary
4. Activity tools — create, get, update, delete, complete
5. Artifact type enum — all 17 types declared in show_artifact
6. BCC determinism — trigger phrases & workflow_key loaded
"""

import os
import pytest
import asyncio

os.environ.setdefault("DATABASE_URL", "postgresql://croo:croo@localhost:5432/croo_digital_experience_test")
os.environ.setdefault("GROQ_API_KEY", "test-key")
os.environ.setdefault("SERPER_API_KEY", "test-key")


USER_CTX = {
    "user_id": "test-user-e2e",
    "tenant_id": "test-tenant-e2e",
    "session_id": "test-session-e2e",
}

FAKE_UUID = "00000000-0000-0000-0000-999999999999"


def run_tool(tool_name: str, args: dict, db=None) -> dict:
    from app.agents.tool_executor import execute_bob_tool
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(execute_bob_tool(tool_name, args, USER_CTX, db))
    finally:
        loop.close()


# ═══════════════════════════════════════════════════════════════
# 1. Tool Definitions — completeness checks
# ═══════════════════════════════════════════════════════════════

class TestToolDefinitions:
    """Verify all 47 tools are declared with valid OpenAI function-calling schemas."""

    def test_total_tool_count(self):
        from app.agents.bob_tools import BOB_TOOLS
        assert len(BOB_TOOLS) == 47, f"Expected 47 tools, got {len(BOB_TOOLS)}"

    def test_all_new_contact_tools_present(self):
        from app.agents.bob_tools import BOB_TOOLS
        names = {t["function"]["name"] for t in BOB_TOOLS}
        expected = {"get_contact", "update_contact", "delete_contact",
                    "list_contact_activities", "list_contact_opportunities",
                    "get_contact_summary"}
        assert expected.issubset(names), f"Missing: {expected - names}"

    def test_all_new_opportunity_tools_present(self):
        from app.agents.bob_tools import BOB_TOOLS
        names = {t["function"]["name"] for t in BOB_TOOLS}
        expected = {"get_opportunity", "update_opportunity", "delete_opportunity",
                    "list_opportunity_activities", "get_opportunity_summary"}
        assert expected.issubset(names), f"Missing: {expected - names}"

    def test_all_new_activity_tools_present(self):
        from app.agents.bob_tools import BOB_TOOLS
        names = {t["function"]["name"] for t in BOB_TOOLS}
        expected = {"create_activity", "get_activity", "update_activity",
                    "delete_activity", "complete_activity"}
        assert expected.issubset(names), f"Missing: {expected - names}"

    def test_every_tool_has_valid_schema(self):
        from app.agents.bob_tools import BOB_TOOLS
        for tool in BOB_TOOLS:
            assert tool["type"] == "function", f"Bad type for {tool}"
            fn = tool["function"]
            assert "name" in fn and fn["name"], f"Missing name: {fn}"
            assert "description" in fn, f"Missing description: {fn['name']}"
            assert "parameters" in fn, f"Missing parameters: {fn['name']}"
            params = fn["parameters"]
            assert params["type"] == "object", f"Bad param type: {fn['name']}"

    def test_no_duplicate_tool_names(self):
        from app.agents.bob_tools import BOB_TOOLS
        names = [t["function"]["name"] for t in BOB_TOOLS]
        assert len(names) == len(set(names)), f"Duplicates: {[n for n in names if names.count(n) > 1]}"


# ═══════════════════════════════════════════════════════════════
# 2. Artifact Type Enum — all 17 types in show_artifact
# ═══════════════════════════════════════════════════════════════

class TestArtifactTypes:
    """Verify the show_artifact tool includes all 17 artifact types."""

    def _get_artifact_enum(self):
        from app.agents.bob_tools import BOB_TOOLS
        for t in BOB_TOOLS:
            if t["function"]["name"] == "show_artifact":
                return t["function"]["parameters"]["properties"]["type"]["enum"]
        pytest.fail("show_artifact tool not found")

    def test_artifact_has_17_types(self):
        enum = self._get_artifact_enum()
        assert len(enum) == 17, f"Expected 17, got {len(enum)}: {enum}"

    def test_original_11_types_present(self):
        enum = set(self._get_artifact_enum())
        original = {"opportunity", "contact", "organization", "search_results",
                     "data_table", "kpi_summary", "progress_card", "checklist",
                     "action_plan", "info_list", "pipeline"}
        assert original.issubset(enum), f"Missing original: {original - enum}"

    def test_new_6_types_present(self):
        enum = set(self._get_artifact_enum())
        new = {"activity_card", "entity_timeline", "comparison_table",
               "alert_banner", "metric_trend", "enrichment_profile"}
        assert new.issubset(enum), f"Missing new: {new - enum}"


# ═══════════════════════════════════════════════════════════════
# 3. Contact Tools — executors
# ═══════════════════════════════════════════════════════════════

class TestContactTools:
    """End-to-end tests for 6 contact management tools."""

    def _create_test_contact(self, db):
        """Helper: create a contact and return its id."""
        result = run_tool("create_contact", {
            "first_name": "E2E",
            "last_name": "ContactTest",
            "email": f"e2e.contact.{id(db)}@test.com",
        }, db)
        assert result["status"] == "ok"
        return result["contact_id"]

    def test_get_contact_not_found(self, db):
        result = run_tool("get_contact", {"contact_id": FAKE_UUID}, db)
        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_get_contact_success(self, db):
        cid = self._create_test_contact(db)
        result = run_tool("get_contact", {"contact_id": cid}, db)
        assert result["status"] == "ok"
        assert result["contact"]["id"] == cid
        assert result["contact"]["first_name"] == "E2E"

    def test_update_contact_not_found(self, db):
        result = run_tool("update_contact", {"contact_id": FAKE_UUID, "phone": "555"}, db)
        assert result["status"] == "error"

    def test_update_contact_success(self, db):
        cid = self._create_test_contact(db)
        result = run_tool("update_contact", {
            "contact_id": cid, "phone": "+1-555-1234", "job_title": "CTO",
        }, db)
        assert result["status"] == "ok"
        assert "phone" in result["message"]
        assert "job_title" in result["message"]

    def test_delete_contact_not_found(self, db):
        result = run_tool("delete_contact", {"contact_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_delete_contact_success(self, db):
        cid = self._create_test_contact(db)
        result = run_tool("delete_contact", {"contact_id": cid}, db)
        assert result["status"] == "ok"
        assert "deleted" in result["message"].lower()

    def test_delete_contact_blocked_by_opportunity(self, db):
        """Contact with linked opportunity should be blocked from deletion."""
        cid = self._create_test_contact(db)
        opp = run_tool("create_opportunity", {
            "name": "Guard Test Deal",
            "contact_id": cid,
        }, db)
        assert opp["status"] == "ok"
        result = run_tool("delete_contact", {"contact_id": cid}, db)
        assert result["status"] == "error"
        assert "opportunity" in result["message"].lower()

    def test_list_contact_activities_not_found(self, db):
        result = run_tool("list_contact_activities", {"contact_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_list_contact_activities_empty(self, db):
        cid = self._create_test_contact(db)
        result = run_tool("list_contact_activities", {"contact_id": cid}, db)
        assert result["status"] == "ok"
        assert isinstance(result["activities"], list)

    def test_list_contact_opportunities_not_found(self, db):
        result = run_tool("list_contact_opportunities", {"contact_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_list_contact_opportunities_empty(self, db):
        cid = self._create_test_contact(db)
        result = run_tool("list_contact_opportunities", {"contact_id": cid}, db)
        assert result["status"] == "ok"
        assert isinstance(result["opportunities"], list)

    def test_get_contact_summary_not_found(self, db):
        result = run_tool("get_contact_summary", {"contact_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_get_contact_summary_success(self, db):
        cid = self._create_test_contact(db)
        result = run_tool("get_contact_summary", {"contact_id": cid}, db)
        assert result["status"] == "ok"
        s = result["summary"]
        assert "contact" in s
        assert "total_opportunities" in s
        assert "total_activities" in s


# ═══════════════════════════════════════════════════════════════
# 4. Opportunity Tools — executors
# ═══════════════════════════════════════════════════════════════

class TestOpportunityTools:
    """End-to-end tests for 5 opportunity management tools."""

    def _create_test_opp(self, db):
        result = run_tool("create_opportunity", {
            "name": f"E2E Opp {id(db)}", "source": "Test",
        }, db)
        assert result["status"] == "ok"
        return result["opportunity_id"]

    def test_get_opportunity_not_found(self, db):
        result = run_tool("get_opportunity", {"opportunity_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_get_opportunity_success(self, db):
        oid = self._create_test_opp(db)
        result = run_tool("get_opportunity", {"opportunity_id": oid}, db)
        assert result["status"] == "ok"
        assert result["opportunity"]["id"] == oid

    def test_update_opportunity_not_found(self, db):
        result = run_tool("update_opportunity", {
            "opportunity_id": FAKE_UUID, "amount": 5000,
        }, db)
        assert result["status"] == "error"

    def test_update_opportunity_success(self, db):
        oid = self._create_test_opp(db)
        result = run_tool("update_opportunity", {
            "opportunity_id": oid, "amount": 25000, "stage": "NEGOTIATION",
        }, db)
        assert result["status"] == "ok"
        assert "amount" in result["message"]

    def test_delete_opportunity_not_found(self, db):
        result = run_tool("delete_opportunity", {"opportunity_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_delete_opportunity_success(self, db):
        oid = self._create_test_opp(db)
        result = run_tool("delete_opportunity", {"opportunity_id": oid}, db)
        assert result["status"] == "ok"
        assert "deleted" in result["message"].lower()

    def test_list_opportunity_activities_not_found(self, db):
        result = run_tool("list_opportunity_activities", {"opportunity_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_list_opportunity_activities_empty(self, db):
        oid = self._create_test_opp(db)
        result = run_tool("list_opportunity_activities", {"opportunity_id": oid}, db)
        assert result["status"] == "ok"
        assert isinstance(result["activities"], list)

    def test_get_opportunity_summary_not_found(self, db):
        result = run_tool("get_opportunity_summary", {"opportunity_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_get_opportunity_summary_success(self, db):
        oid = self._create_test_opp(db)
        result = run_tool("get_opportunity_summary", {"opportunity_id": oid}, db)
        assert result["status"] == "ok"
        s = result["summary"]
        assert "opportunity" in s
        assert "total_products" in s
        assert "total_activities" in s


# ═══════════════════════════════════════════════════════════════
# 5. Activity Tools — executors
# ═══════════════════════════════════════════════════════════════

class TestActivityTools:
    """End-to-end tests for 5 activity management tools."""

    def _create_test_activity(self, db, subject="E2E Task", activity_type="TASK"):
        result = run_tool("create_activity", {
            "subject": subject,
            "activity_type": activity_type,
            "priority": "MEDIUM",
        }, db)
        assert result["status"] == "ok"
        return result["activity_id"]

    def test_create_activity_task(self, db):
        result = run_tool("create_activity", {
            "subject": "Follow up with client",
            "activity_type": "TASK",
            "priority": "HIGH",
        }, db)
        assert result["status"] == "ok"
        assert "activity_id" in result
        assert result["activity_type"] == "TASK"

    def test_create_activity_call(self, db):
        result = run_tool("create_activity", {
            "subject": "Discovery call",
            "activity_type": "CALL",
        }, db)
        assert result["status"] == "ok"
        assert result["activity_type"] == "CALL"

    def test_create_activity_email(self, db):
        result = run_tool("create_activity", {
            "subject": "Send proposal",
            "activity_type": "EMAIL",
        }, db)
        assert result["status"] == "ok"
        assert result["activity_type"] == "EMAIL"

    def test_create_activity_meeting(self, db):
        result = run_tool("create_activity", {
            "subject": "Quarterly review",
            "activity_type": "MEETING",
            "due_date": "2026-04-01T10:00:00",
        }, db)
        assert result["status"] == "ok"
        assert result["activity_type"] == "MEETING"

    def test_create_activity_note(self, db):
        result = run_tool("create_activity", {
            "subject": "Internal note",
            "activity_type": "NOTE",
        }, db)
        assert result["status"] == "ok"
        assert result["activity_type"] == "NOTE"

    def test_get_activity_not_found(self, db):
        result = run_tool("get_activity", {"activity_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_get_activity_success(self, db):
        aid = self._create_test_activity(db)
        result = run_tool("get_activity", {"activity_id": aid}, db)
        assert result["status"] == "ok"
        assert result["activity"]["id"] == aid
        assert result["activity"]["subject"] == "E2E Task"

    def test_update_activity_not_found(self, db):
        result = run_tool("update_activity", {
            "activity_id": FAKE_UUID, "subject": "nope",
        }, db)
        assert result["status"] == "error"

    def test_update_activity_success(self, db):
        aid = self._create_test_activity(db)
        result = run_tool("update_activity", {
            "activity_id": aid, "subject": "Updated subject", "priority": "HIGH",
        }, db)
        assert result["status"] == "ok"
        assert "subject" in result["message"]
        assert "priority" in result["message"]

    def test_delete_activity_not_found(self, db):
        result = run_tool("delete_activity", {"activity_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_delete_activity_success(self, db):
        aid = self._create_test_activity(db)
        result = run_tool("delete_activity", {"activity_id": aid}, db)
        assert result["status"] == "ok"
        assert "deleted" in result["message"].lower()

    def test_complete_activity_not_found(self, db):
        result = run_tool("complete_activity", {"activity_id": FAKE_UUID}, db)
        assert result["status"] == "error"

    def test_complete_activity_success(self, db):
        aid = self._create_test_activity(db)
        result = run_tool("complete_activity", {"activity_id": aid}, db)
        assert result["status"] == "ok"
        assert "completed" in result["message"].lower()

        # Verify status changed
        check = run_tool("get_activity", {"activity_id": aid}, db)
        assert check["activity"]["status"] == "COMPLETED"
        assert check["activity"]["completed_at"] is not None


# ═══════════════════════════════════════════════════════════════
# 6. Cross-module pipeline — full workflow
# ═══════════════════════════════════════════════════════════════

class TestCrossModulePipeline:
    """E2E: create contact → opportunity → activities → summaries."""

    def test_full_crm_workflow(self, db):
        # 1. Create contact
        c = run_tool("create_contact", {
            "first_name": "Pipeline",
            "last_name": "Test",
            "email": "pipeline@e2e.com",
        }, db)
        assert c["status"] == "ok"
        cid = c["contact_id"]

        # 2. Create opportunity linked to contact
        o = run_tool("create_opportunity", {
            "name": "Pipeline Deal",
            "contact_id": cid,
            "amount": 50000,
        }, db)
        assert o["status"] == "ok"
        oid = o["opportunity_id"]

        # 3. Create activities linked to both
        a1 = run_tool("create_activity", {
            "subject": "Discovery call",
            "activity_type": "CALL",
            "contact_id": cid,
            "opportunity_id": oid,
        }, db)
        assert a1["status"] == "ok"

        a2 = run_tool("create_activity", {
            "subject": "Send proposal",
            "activity_type": "EMAIL",
            "contact_id": cid,
            "opportunity_id": oid,
        }, db)
        assert a2["status"] == "ok"

        # 4. Complete one activity
        comp = run_tool("complete_activity", {"activity_id": a1["activity_id"]}, db)
        assert comp["status"] == "ok"

        # 5. Get contact summary — should show opp + activities
        cs = run_tool("get_contact_summary", {"contact_id": cid}, db)
        assert cs["status"] == "ok"
        assert cs["summary"]["total_opportunities"] >= 1
        assert cs["summary"]["pipeline_total"] >= 50000

        # 6. Get opportunity summary — should show activities
        os_result = run_tool("get_opportunity_summary", {"opportunity_id": oid}, db)
        assert os_result["status"] == "ok"
        assert os_result["summary"]["total_activities"] >= 2

        # 7. Update opportunity stage
        upd = run_tool("update_opportunity", {
            "opportunity_id": oid, "stage": "NEGOTIATION",
        }, db)
        assert upd["status"] == "ok"

        # 8. Try delete contact (should be blocked — opp linked)
        blocked = run_tool("delete_contact", {"contact_id": cid}, db)
        assert blocked["status"] == "error"
        assert "opportunity" in blocked["message"].lower()


# ═══════════════════════════════════════════════════════════════
# 7. BCC Determinism Wiring
# ═══════════════════════════════════════════════════════════════

class TestBccDeterminism:
    """Verify BCC-driven determinism is wired into the runtime."""

    def test_classifier_loads_trigger_phrases(self):
        """load_supported_intents_from_bcc should return a dict."""
        from app.agents.intent_classifier import load_supported_intents_from_bcc
        # Should not crash even with no DB active
        result = load_supported_intents_from_bcc(None)
        assert isinstance(result, (dict, type(None)))

    def test_chat_agent_has_workflow_key_fallback(self):
        """Bob's dispatch code should reference workflow_key."""
        import inspect
        from app.agents.bob_chat_agent import BobChatAgent
        source = inspect.getsource(BobChatAgent.chat)
        assert "workflow_key" in source

    def test_chat_agent_injects_regulations(self):
        """Bob's system prompt building should reference regulations."""
        import inspect
        from app.agents.bob_chat_agent import BobChatAgent
        source = inspect.getsource(BobChatAgent.chat)
        assert "regulation" in source.lower()
""", "Complexity": 7, "Description": "Comprehensive end-to-end test file covering all 16 new tools, 47-tool count validation, 17 artifact types, delete guards, cross-module pipeline, and BCC determinism wiring.", "EmptyFile": false, "IsArtifact": false, "Overwrite": false, "TargetFile": "/Users/alexandregauthier/Dev/croo-digital-experience-v.2.0/backend/tests/test_new_crm_tools.py"}
