"""Tests for Deep Agent plan_validator_node — trigger phrase collision logic."""

from unittest.mock import patch

from app.agents.deep_agent_graph import plan_validator_node, DeepAgentState


def _make_state(plan: dict, tenant_id: str = "t1") -> DeepAgentState:
    """Helper to build a minimal DeepAgentState for validation."""
    return {
        "tenant_id": tenant_id,
        "user_id": "u1",
        "user_email": "test@test.com",
        "instruction": "test",
        "plan": plan,
        "domains_created": [],
        "intents_created": [],
        "tasks_created": [],
        "generated_tool_schemas": [],
        "generated_code": {},
        "code_review_result": {},
        "review_result": {},
        "status": "validating",
        "error": None,
        "revision_count": 0,
    }


def _plan_with_intent(
    intent_name: str,
    trigger_phrases: list[str],
    db_table: str = "contacts",
    needs_workflow: bool = True,
) -> dict:
    """Build a minimal plan with one domain and one intent."""
    return {
        "domains": [
            {
                "name": "Test Domain",
                "intents": [
                    {
                        "name": intent_name,
                        "workflow_key": intent_name,
                        "needs_workflow": needs_workflow,
                        "trigger_phrases": trigger_phrases,
                        "tasks": [
                            {
                                "name": "Task 1",
                                "tool_name": None,
                                "sort_order": 0,
                                "context": {"db_table": db_table},
                            }
                        ],
                    }
                ],
            }
        ]
    }


# ── Fixtures for mocking DB helpers ──────────────────────────

EMPTY_TRIGGERS: dict[str, list[str]] = {}
EMPTY_WORKFLOWS: list[str] = []


def _patch_helpers(existing_triggers=None, existing_workflows=None):
    """Convenience: patch both _load helpers at once."""
    triggers = existing_triggers if existing_triggers is not None else EMPTY_TRIGGERS
    workflows = existing_workflows if existing_workflows is not None else EMPTY_WORKFLOWS
    return (
        patch(
            "app.agents.deep_agent_graph._load_existing_trigger_phrases_dict",
            return_value=triggers,
        ),
        patch(
            "app.agents.deep_agent_graph._load_existing_workflow_keys",
            return_value=workflows,
        ),
    )


# ── Tests ─────────────────────────────────────────────────────


class TestPlanValidatorCollisions:
    """Trigger phrase collision detection."""

    def test_no_collision_on_new_phrases(self):
        """Brand-new phrases should pass validation."""
        plan = _plan_with_intent(
            "add_candidate",
            ["ajoute un candidat", "new candidate", "add applicant"],
            needs_workflow=False,
        )
        state = _make_state(plan)
        p1, p2 = _patch_helpers()
        with p1, p2:
            result = plan_validator_node(state)
        assert result["status"] == "building"
        assert result["review_result"]["approved"] is True

    def test_collision_with_existing_intent(self):
        """Phrase owned by a different intent must be caught."""
        existing_triggers = {
            "add_contact": ["ajoute un contact", "new contact"],
        }
        plan = _plan_with_intent(
            "add_candidate",
            ["ajoute un contact", "new candidate"],  # first phrase collides
            needs_workflow=False,
        )
        state = _make_state(plan)
        p1, p2 = _patch_helpers(existing_triggers=existing_triggers)
        with p1, p2:
            result = plan_validator_node(state)
        assert result["status"] == "planning"  # sent back for revision
        issues = result["review_result"]["issues"]
        assert len(issues) == 1
        assert "ajoute un contact" in issues[0]

    def test_collision_error_includes_owner(self):
        """The error message must name the existing intent that owns the phrase."""
        existing_triggers = {
            "add_contact": ["ajoute un contact", "new contact"],
        }
        plan = _plan_with_intent(
            "add_candidate",
            ["ajoute un contact"],
            needs_workflow=False,
        )
        state = _make_state(plan)
        p1, p2 = _patch_helpers(existing_triggers=existing_triggers)
        with p1, p2:
            result = plan_validator_node(state)
        issue = result["review_result"]["issues"][0]
        assert "add_contact" in issue, f"Expected 'add_contact' in error: {issue}"

    def test_idempotent_retry(self):
        """Re-submitting the same plan should NOT collide with its own intents."""
        # Simulate DB state left by a previous failed run of this same plan.
        existing_triggers = {
            "add_candidate": [
                "ajoute un candidat",
                "new candidate",
                "add applicant",
            ],
        }
        plan = _plan_with_intent(
            "add_candidate",
            ["ajoute un candidat", "new candidate", "add applicant"],
            needs_workflow=False,
        )
        state = _make_state(plan)
        p1, p2 = _patch_helpers(existing_triggers=existing_triggers)
        with p1, p2:
            result = plan_validator_node(state)
        # Should pass — the validator skips phrases from intents matching
        # the plan's own intent names.
        assert result["status"] == "building"
        assert result["review_result"]["approved"] is True

    def test_intra_plan_duplicate(self):
        """Two intents in the same plan sharing a phrase should be caught."""
        plan = {
            "domains": [
                {
                    "name": "HR",
                    "intents": [
                        {
                            "name": "add_candidate",
                            "workflow_key": "add_candidate",
                            "needs_workflow": False,
                            "trigger_phrases": [
                                "ajoute un candidat",
                                "new candidate",
                            ],
                            "tasks": [
                                {
                                    "name": "T1",
                                    "tool_name": None,
                                    "sort_order": 0,
                                    "context": {"db_table": "contacts"},
                                }
                            ],
                        },
                        {
                            "name": "schedule_interview",
                            "workflow_key": "schedule_interview",
                            "needs_workflow": False,
                            "trigger_phrases": [
                                "new candidate",  # duplicate!
                                "schedule interview",
                            ],
                            "tasks": [
                                {
                                    "name": "T2",
                                    "tool_name": None,
                                    "sort_order": 0,
                                    "context": {"db_table": "activities"},
                                }
                            ],
                        },
                    ],
                }
            ]
        }
        state = _make_state(plan)
        p1, p2 = _patch_helpers()
        with p1, p2:
            result = plan_validator_node(state)
        assert result["status"] == "planning"
        issues = result["review_result"]["issues"]
        dup_issues = [i for i in issues if "duplicates" in i]
        assert len(dup_issues) == 1
        assert "new candidate" in dup_issues[0]
        assert "add_candidate" in dup_issues[0]

    def test_invalid_db_table(self):
        """A task referencing a non-existent table must be caught."""
        plan = _plan_with_intent(
            "add_candidate",
            ["ajoute un candidat"],
            db_table="candidates",  # invalid!
            needs_workflow=False,
        )
        state = _make_state(plan)
        p1, p2 = _patch_helpers()
        with p1, p2:
            result = plan_validator_node(state)
        assert result["status"] == "planning"
        issues = result["review_result"]["issues"]
        table_issues = [i for i in issues if "candidates" in i]
        assert len(table_issues) == 1
