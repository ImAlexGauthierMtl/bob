"""Dynamic workflow runner — builds LangGraph from WorkflowStep definitions.

Each workflow is compiled into a dynamic LangGraph at runtime.
Steps are agent nodes with configurable behavior.
"""

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.workflow import Workflow, WorkflowStep
from app.domain.entities.workflow_execution import WorkflowExecution, WorkflowStepExecution
from app.infrastructure.persistence.workflow_repository import WorkflowRepository
from app.application.services.capability_resolver import CapabilityResolver
from app.domain.entities.user import User

logger = structlog.get_logger(__name__)


# ── Built-in agent node functions ─────────────────

def node_log_action(state: dict) -> dict:
    """Log an action — simplest node for debugging/audit."""
    logger.info("workflow_node_log", step=state.get("current_step_name"), data=state.get("input_data"))
    return {**state, "output_data": {"logged": True}}


def node_notify(state: dict) -> dict:
    """Send a notification (placeholder)."""
    config = state.get("step_config", {})
    logger.info("workflow_node_notify", target=config.get("target"), message=config.get("message"))
    return {**state, "output_data": {"notified": True, "target": config.get("target")}}


def node_ai_analyze(state: dict) -> dict:
    """Run AI analysis on input data using Groq."""
    from app.agents.llm_client import llm_client
    import json

    config = state.get("step_config", {})
    prompt = config.get("prompt", "Analyze the following data and provide insights.")
    input_data = state.get("input_data", {})

    try:
        response = llm_client.chat(
            prompt=f"{prompt}\n\nData:\n{json.dumps(input_data, default=str)}",
            system_prompt="You are an AI analysis agent. Provide structured insights in JSON format.",
            json_mode=True,
            temperature=0.1,
            # ── Usage tracking context ──
            tenant_id=state.get("tenant_id"),
            user_id=state.get("user_id"),
            trigger_source="WORKFLOW",
            correlation_id=state.get("execution_id", ""),
        )
        result = json.loads(response)
        return {**state, "output_data": result, "confidence": 0.8}
    except Exception as e:
        logger.error("workflow_ai_analyze_error", error=str(e))
        return {**state, "output_data": {"error": str(e)}, "confidence": 0.0}


def node_condition(state: dict) -> dict:
    """Evaluate a condition — routes to on_success or on_failure."""
    config = state.get("step_config", {})
    field = config.get("field")
    operator = config.get("operator", "equals")
    value = config.get("value")
    input_data = state.get("input_data", {})

    actual = input_data.get(field)

    if operator == "equals":
        passed = actual == value
    elif operator == "not_equals":
        passed = actual != value
    elif operator == "contains":
        passed = value in str(actual) if actual else False
    elif operator == "exists":
        passed = actual is not None
    elif operator == "gt":
        passed = float(actual) > float(value) if actual else False
    elif operator == "lt":
        passed = float(actual) < float(value) if actual else False
    else:
        passed = False

    return {**state, "condition_passed": passed, "output_data": {"field": field, "passed": passed}}


def node_human_approval(state: dict) -> dict:
    """Mark step as pending human approval."""
    return {**state, "status": "pending_approval", "output_data": {"awaiting_approval": True}}


def node_trigger(state: dict) -> dict:
    """Trigger passthrough — marks the workflow entry point."""
    logger.info("workflow_node_trigger", step=state.get("current_step_name"))
    return {**state, "output_data": {"triggered": True}}


# Registry of built-in nodes
AGENT_NODE_REGISTRY: dict[str, Any] = {
    "log_action": node_log_action,
    "notify": node_notify,
    "ai_analyze": node_ai_analyze,
    "ai_analysis": node_ai_analyze,  # alias — step_type fallback
    "condition": node_condition,
    "human_approval": node_human_approval,
    "trigger": node_trigger,
    "action": node_log_action,  # default action → log
}


class WorkflowRunner:
    """Executes a workflow by walking its step graph."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = WorkflowRepository(db)

    async def run(
        self,
        workflow: Workflow,
        user: User,
        tenant_id: str,
        input_data: dict | None = None,
        triggered_by: str = "manual",
    ) -> WorkflowExecution:
        """Execute a workflow for a user."""
        steps = self.repo.get_steps(workflow.id)
        if not steps:
            raise ValueError(f"Workflow '{workflow.name}' has no steps")

        # Check capabilities
        resolver = CapabilityResolver(self.db)
        if workflow.required_capabilities:
            for cap in workflow.required_capabilities:
                if not resolver.can(user.id, cap, tenant_id):
                    raise PermissionError(f"Missing capability: {cap}")

        # Determine effective execution mode
        agent_mode = resolver.get_agent_mode(user)
        effective_mode = self._resolve_execution_mode(workflow.execution_mode, agent_mode)

        # Create execution record
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            triggered_by=triggered_by,
            trigger_type=workflow.trigger_type,
            status="running",
            input_data=input_data,
            steps_total=len(steps),
            tenant_id=tenant_id,
        )
        execution = self.repo.create_execution(execution)

        logger.info(
            "workflow_execution_start",
            workflow=workflow.name,
            execution_id=execution.id,
            steps=len(steps),
            mode=effective_mode,
        )

        # Find entry point
        entry = next((s for s in steps if s.is_entry_point), steps[0])
        step_map = {s.id: s for s in steps}
        # Build ordered step list for sequential fallback
        ordered_steps = sorted(steps, key=lambda s: s.step_order)

        # Walk the graph
        current_step = entry
        state = {"input_data": input_data or {}, "execution_id": execution.id}

        while current_step:
            step_exe = await self._execute_step(
                current_step, state, execution, effective_mode
            )

            execution.steps_completed += 1
            self.repo.update_execution(execution)

            # Check if we need to stop (approval, failure)
            if step_exe.status == "pending_approval":
                execution.status = "pending_approval"
                self.repo.update_execution(execution)
                break
            elif step_exe.status == "failed":
                next_id = current_step.on_failure
                if not next_id:
                    execution.status = "failed"
                    execution.error = step_exe.error
                    execution.completed_at = datetime.now(timezone.utc)
                    self.repo.update_execution(execution)
                    break
                current_step = step_map.get(next_id)
            else:
                # Success path
                state["input_data"] = step_exe.output_data or state["input_data"]
                if current_step.on_success:
                    # Explicit jump
                    current_step = step_map.get(current_step.on_success)
                else:
                    # Fallback: next step by step_order
                    idx = next(
                        (i for i, s in enumerate(ordered_steps) if s.id == current_step.id),
                        -1,
                    )
                    current_step = ordered_steps[idx + 1] if idx + 1 < len(ordered_steps) else None

        # If we exited normally (no more steps)
        if execution.status == "running":
            execution.status = "completed"
            execution.completed_at = datetime.now(timezone.utc)
            if execution.started_at:
                delta = execution.completed_at - execution.started_at
                execution.duration_ms = int(delta.total_seconds() * 1000)
            execution.output_data = state.get("input_data")
            self.repo.update_execution(execution)

        logger.info(
            "workflow_execution_done",
            workflow=workflow.name,
            execution_id=execution.id,
            status=execution.status,
            steps_completed=execution.steps_completed,
        )

        return execution

    async def _execute_step(
        self,
        step: WorkflowStep,
        state: dict,
        execution: WorkflowExecution,
        effective_mode: str,
    ) -> WorkflowStepExecution:
        """Execute a single workflow step."""
        step_exe = WorkflowStepExecution(
            execution_id=execution.id,
            step_id=step.id,
            status="running",
            input_data=state.get("input_data"),
            agent_mode_used=effective_mode,
        )
        step_exe = self.repo.create_step_execution(step_exe)

        try:
            # Get the node function
            node_fn = AGENT_NODE_REGISTRY.get(step.agent_node or step.step_type)
            if not node_fn:
                raise ValueError(f"Unknown agent node: {step.agent_node or step.step_type}")

            # Build step state
            step_state = {
                **state,
                "current_step_name": step.name,
                "step_config": step.config or {},
                "effective_mode": effective_mode,
            }

            # Execute
            result = node_fn(step_state)

            step_exe.status = result.get("status", "completed")
            step_exe.output_data = result.get("output_data")
            step_exe.confidence_score = result.get("confidence")
            step_exe.completed_at = datetime.now(timezone.utc)
            if step_exe.started_at:
                delta = step_exe.completed_at - step_exe.started_at
                step_exe.duration_ms = int(delta.total_seconds() * 1000)

        except Exception as e:
            logger.error("workflow_step_error", step=step.name, error=str(e))
            step_exe.status = "failed"
            step_exe.error = str(e)
            step_exe.completed_at = datetime.now(timezone.utc)

        self.repo.update_step_execution(step_exe)
        return step_exe

    def _resolve_execution_mode(self, workflow_mode: str, user_agent_mode: str) -> str:
        """Resolve effective execution mode.

        The user's trust-level caps the workflow's requested mode.
        """
        mode_rank = {"suggest": 0, "approval": 1, "auto": 2}
        wf_rank = mode_rank.get(workflow_mode, 0)
        user_rank = mode_rank.get(user_agent_mode, 0)
        effective_rank = min(wf_rank, user_rank)
        return {0: "suggest", 1: "approval", 2: "auto"}[effective_rank]
