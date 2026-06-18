from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt

import main
from app.domain.entities.workflow import Workflow, WorkflowStep
from app.domain.entities.workflow_execution import WorkflowExecution, WorkflowStepExecution
from app.events import publishers
from app.infrastructure import database
from app.infrastructure.persistence.workflow_repository import WorkflowRepository
from app.middleware.auth import get_current_user, settings
from app.presentation.routes import workflow_routes
from app.presentation.schemas import workflow_schemas


USER = {"user_id": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"}
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_workflow(workflow_id="wf-1", **overrides):
    wf = Workflow(
        id=workflow_id,
        name="Workflow",
        description="Useful workflow",
        level="company",
        owner_id="user-1",
        owner_type="user",
        trigger_type="manual",
        trigger_config={"source": "test"},
        execution_mode="suggest",
        required_capabilities=["workflow.run"],
        is_overridable=True,
        override_policy="choice",
        overrides_workflow_id=None,
        is_active=True,
        is_template=False,
        module="crm",
        category="sales",
        tenant_id="tenant-1",
        created_by="user@example.com",
        updated_by=None,
    )
    wf.created_at = NOW
    wf.updated_at = NOW
    wf.version = 1
    wf.is_deleted = False
    for key, value in overrides.items():
        setattr(wf, key, value)
    return wf


def make_step(step_id="step-1", workflow_id="wf-1", **overrides):
    step = WorkflowStep(
        id=step_id,
        workflow_id=workflow_id,
        name="First step",
        step_order=0,
        step_type="agent",
        agent_node="bob",
        config={"prompt": "Help"},
        on_success=None,
        on_failure=None,
        description="Run the agent",
        is_entry_point=True,
    )
    for key, value in overrides.items():
        setattr(step, key, value)
    return step


def make_execution(execution_id="exe-1", workflow_id="wf-1", **overrides):
    exe = WorkflowExecution(
        id=execution_id,
        workflow_id=workflow_id,
        triggered_by="user@example.com",
        trigger_type="manual",
        status="running",
        input_data={"contact_id": "contact-1"},
        output_data=None,
        error=None,
        steps_completed=0,
        steps_total=1,
        duration_ms=None,
        tenant_id="tenant-1",
    )
    exe.started_at = NOW
    exe.completed_at = None
    for key, value in overrides.items():
        setattr(exe, key, value)
    return exe


def make_step_execution(step_execution_id="step-exe-1", execution_id="exe-1", step_id="step-1"):
    step_exe = WorkflowStepExecution(
        id=step_execution_id,
        execution_id=execution_id,
        step_id=step_id,
        status="completed",
        input_data={},
        output_data={"ok": True},
        error=None,
        agent_mode_used="suggest",
        confidence_score=0.9,
        duration_ms=12,
    )
    step_exe.started_at = NOW
    step_exe.completed_at = NOW
    return step_exe


class FakeWorkflowRepository:
    def __init__(self, db):
        self.db = db
        self.workflows = {"wf-1": make_workflow()}
        self.steps = {"wf-1": [make_step()]}
        self.executions = {"exe-1": make_execution()}
        self.step_executions = {"exe-1": [make_step_execution()]}

    def create(self, wf):
        wf.id = "wf-new"
        wf.created_at = NOW
        wf.updated_at = NOW
        wf.is_active = True
        wf.is_deleted = False
        wf.version = 1
        self.workflows[wf.id] = wf
        return wf

    def get_by_id(self, wf_id, tenant_id):
        wf = self.workflows.get(wf_id)
        return wf if wf and wf.tenant_id == tenant_id and not wf.is_deleted else None

    def list_all(self, tenant_id, level=None, module=None, is_template=None, skip=0, limit=50):
        items = [wf for wf in self.workflows.values() if wf.tenant_id == tenant_id and not wf.is_deleted]
        if level:
            items = [wf for wf in items if wf.level == level]
        if module:
            items = [wf for wf in items if wf.module == module]
        if is_template is not None:
            items = [wf for wf in items if wf.is_template == is_template]
        return items[skip : skip + limit]

    def count(self, tenant_id, level=None):
        return len(self.list_all(tenant_id, level=level))

    def update(self, wf):
        wf.updated_at = NOW
        wf.version = (wf.version or 0) + 1
        return wf

    def soft_delete(self, wf, deleted_by):
        wf.is_deleted = True
        wf.deleted_by = deleted_by
        return wf

    def add_step(self, step):
        step.id = step.id or "step-new"
        self.steps.setdefault(step.workflow_id, []).append(step)
        return step

    def get_steps(self, workflow_id):
        return self.steps.get(workflow_id, [])

    def get_step_by_id(self, step_id):
        for steps in self.steps.values():
            for step in steps:
                if step.id == step_id:
                    return step
        return None

    def update_step(self, step):
        return step

    def delete_step(self, step_id):
        for workflow_id, steps in self.steps.items():
            self.steps[workflow_id] = [step for step in steps if step.id != step_id]

    def delete_all_steps(self, workflow_id):
        self.steps[workflow_id] = []

    def create_execution(self, exe):
        exe.id = "exe-new"
        exe.started_at = NOW
        exe.status = exe.status or "running"
        exe.steps_completed = exe.steps_completed or 0
        exe.steps_total = exe.steps_total or 0
        self.executions[exe.id] = exe
        return exe

    def get_execution(self, exe_id):
        return self.executions.get(exe_id)

    def list_executions(self, workflow_id, limit=20):
        return [exe for exe in self.executions.values() if exe.workflow_id == workflow_id][:limit]

    def update_execution(self, exe):
        return exe

    def create_step_execution(self, step_exe):
        step_exe.id = step_exe.id or "step-exe-new"
        self.step_executions.setdefault(step_exe.execution_id, []).append(step_exe)
        return step_exe

    def update_step_execution(self, step_exe):
        return step_exe

    def get_step_executions(self, execution_id):
        return self.step_executions.get(execution_id, [])


class FakeStatsQuery:
    def filter(self, *args):
        return self

    def first(self):
        return SimpleNamespace(total=4, completed=2, failed=1, running=1, pending=0, avg_duration_ms=18.25)


class FakeExecutionQuery:
    def __init__(self):
        self.items = [make_execution("exe-recent", status="completed", completed_at=NOW, duration_ms=25)]

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def limit(self, limit):
        self.items = self.items[:limit]
        return self

    def all(self):
        return self.items


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.refreshed = []
        self.deleted = False

    def query(self, *entities):
        if entities and entities[0] is WorkflowExecution:
            return FakeExecutionQuery()
        return FakeStatsQuery()

    def add(self, entity):
        self.added.append(entity)

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        self.refreshed.append(entity)


class FakeQuery:
    def __init__(self, result=None, results=None, count_value=1):
        self.result = result
        self.results = list(results or [])
        self.count_value = count_value
        self.deleted = False

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def offset(self, skip):
        self.results = self.results[skip:]
        return self

    def limit(self, limit):
        self.results = self.results[:limit]
        return self

    def first(self):
        return self.result

    def all(self):
        return self.results

    def count(self):
        return self.count_value

    def delete(self):
        self.deleted = True


class RepositorySession(FakeDB):
    def __init__(self):
        super().__init__()
        self.workflow = make_workflow()
        self.step = make_step()
        self.execution = make_execution()
        self.step_execution = make_step_execution()

    def query(self, entity):
        if entity is Workflow:
            return FakeQuery(self.workflow, [self.workflow], 1)
        if entity is WorkflowStep:
            return FakeQuery(self.step, [self.step], 1)
        if entity is WorkflowExecution:
            return FakeQuery(self.execution, [self.execution], 1)
        if entity is WorkflowStepExecution:
            return FakeQuery(self.step_execution, [self.step_execution], 1)
        return FakeQuery()


@pytest.fixture()
def repo():
    return FakeWorkflowRepository(FakeDB())


@pytest.fixture()
def client(monkeypatch, repo):
    async def noop_publish(*args, **kwargs):
        return None

    monkeypatch.setattr(workflow_routes, "WorkflowRepository", lambda db: repo)
    monkeypatch.setattr(publishers.event_bus, "publish", noop_publish)
    monkeypatch.setattr(workflow_routes, "publish_workflow_created", noop_publish)
    monkeypatch.setattr(workflow_routes, "publish_workflow_updated", noop_publish)
    monkeypatch.setattr(workflow_routes, "publish_workflow_deleted", noop_publish)
    monkeypatch.setattr(workflow_routes, "publish_workflow_executed", noop_publish)
    main.app.dependency_overrides[workflow_routes.get_current_user] = lambda: USER
    main.app.dependency_overrides[workflow_routes.get_db] = lambda: FakeDB()
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers():
    token = jwt.encode(
        {"sub": "user-1", "email": "user@example.com", "tenant_id": "tenant-1"},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def test_monitoring_endpoints(client):
    for path in ["/health", "/readiness", "/liveness", "/startup", "/metrics"]:
        response = client.get(path)
        assert response.status_code == 200
    assert "dependencies" in client.get("/health").json()
    assert "cde_api_info" in client.get("/metrics").text


def test_workflow_crud_routes(client):
    created = client.post(
        "/api/v1/workflows",
        json={
            "name": "New workflow",
            "module": "crm",
            "steps": [{"name": "First", "step_type": "agent", "agent_node": "bob"}],
        },
    )
    assert created.status_code == 201
    assert created.json()["id"] == "wf-new"

    listed = client.get("/api/v1/workflows", params={"level": "company", "module": "crm"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/api/v1/workflows/wf-1").json()["id"] == "wf-1"
    assert client.get("/api/v1/workflows/missing").status_code == 404
    assert client.patch("/api/v1/workflows/wf-1", json={"name": "Updated"}).json()["name"] == "Updated"
    assert client.patch("/api/v1/workflows/missing", json={"name": "Updated"}).status_code == 404
    assert client.delete("/api/v1/workflows/wf-1").status_code == 204
    assert client.delete("/api/v1/workflows/missing").status_code == 404


def test_step_and_execution_routes(client):
    assert client.get("/api/v1/workflows/wf-1/steps").json()[0]["id"] == "step-1"
    assert client.get("/api/v1/workflows/missing/steps").status_code == 404
    assert client.post("/api/v1/workflows/wf-1/steps", json={"name": "Second", "step_type": "agent"}).status_code == 201
    assert client.post("/api/v1/workflows/missing/steps", json={"name": "Second", "step_type": "agent"}).status_code == 404
    assert client.patch("/api/v1/workflows/wf-1/steps/step-1", json={"name": "Renamed"}).json()["name"] == "Renamed"
    assert client.patch("/api/v1/workflows/wf-1/steps/missing", json={"name": "Renamed"}).status_code == 404
    assert client.delete("/api/v1/workflows/wf-1/steps/step-1").status_code == 204
    assert client.delete("/api/v1/workflows/wf-1/steps/missing").status_code == 404

    created = client.post("/api/v1/workflows/wf-1/executions", json={"input_data": {"contact_id": "contact-1"}})
    assert created.status_code == 201
    assert created.json()["workflow_id"] == "wf-1"
    assert client.post("/api/v1/workflows/missing/executions", json={}).status_code == 404
    assert client.get("/api/v1/workflows/wf-1/executions").json()[0]["id"] == "exe-1"
    detail = client.get("/api/v1/workflows/wf-1/executions/exe-1").json()
    assert detail["execution"]["id"] == "exe-1"
    assert detail["steps"][0]["id"] == "step-exe-1"
    assert client.get("/api/v1/workflows/wf-1/executions/missing").status_code == 404
    assert client.patch("/api/v1/workflows/wf-1/executions/exe-1", json={"status": "completed"}).json()["status"] == "completed"
    assert client.patch("/api/v1/workflows/wf-1/executions/missing", json={"status": "completed"}).status_code == 404


def test_monitoring_workflow_routes(client):
    stats = client.get("/api/v1/workflows/monitoring/stats").json()
    assert stats["success_rate"] == 50.0
    assert stats["active_workflows"] >= 1
    recent = client.get("/api/v1/workflows/monitoring/recent", params={"limit": 1, "status": "completed"}).json()
    assert recent[0]["id"] == "exe-recent"


def test_auth_dependency_accepts_and_rejects_tokens(auth_headers):
    credentials = type("Credentials", (), {"credentials": auth_headers["Authorization"].split(" ", 1)[1]})()
    assert get_current_user(credentials)["tenant_id"] == "tenant-1"

    invalid = type("Credentials", (), {"credentials": "not-a-token"})()
    with pytest.raises(Exception) as invalid_token:
        get_current_user(invalid)
    assert getattr(invalid_token.value, "status_code", None) == 401

    no_sub = jwt.encode({"email": "user@example.com"}, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    with pytest.raises(Exception) as missing_sub:
        get_current_user(type("Credentials", (), {"credentials": no_sub})())
    assert getattr(missing_sub.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_publishers_emit_domain_events(monkeypatch):
    published = []

    async def fake_publish(event):
        published.append(event)

    monkeypatch.setattr(publishers.event_bus, "publish", fake_publish)
    await publishers.publish_workflow_created("wf-1", {"name": "Workflow"})
    await publishers.publish_workflow_updated("wf-1", {"name": "Updated"})
    await publishers.publish_workflow_deleted("wf-1")
    await publishers.publish_workflow_executed("wf-1", "exe-1", {"triggered_by": "user@example.com"})
    assert [event["type"] for event in published] == [
        "workflow.created",
        "workflow.updated",
        "workflow.deleted",
        "workflow.executed",
    ]


def test_repository_methods_cover_persistence_paths():
    session = RepositorySession()
    repository = WorkflowRepository(session)

    assert repository.create(make_workflow("wf-new")).id == "wf-new"
    assert repository.get_by_id("wf-1", "tenant-1").id == "wf-1"
    assert repository.list_all("tenant-1", level="company", module="crm", is_template=False)[0].id == "wf-1"
    assert repository.count("tenant-1", level="company") == 1
    assert repository.update(session.workflow).version == 2
    assert repository.soft_delete(session.workflow, "user@example.com").is_deleted is True
    assert repository.add_step(make_step("step-new")).id == "step-new"
    assert repository.get_steps("wf-1")[0].id == "step-1"
    assert repository.get_step_by_id("step-1").id == "step-1"
    assert repository.update_step(session.step).id == "step-1"
    repository.delete_step("step-1")
    repository.delete_all_steps("wf-1")
    assert repository.create_execution(make_execution("exe-new")).id == "exe-new"
    assert repository.get_execution("exe-1").id == "exe-1"
    assert repository.list_executions("wf-1")[0].id == "exe-1"
    assert repository.update_execution(session.execution).id == "exe-1"
    assert repository.create_step_execution(make_step_execution("step-exe-new")).id == "step-exe-new"
    assert repository.update_step_execution(session.step_execution).id == "step-exe-1"
    assert repository.get_step_executions("exe-1")[0].id == "step-exe-1"
    assert session.commits >= 1


def test_database_facade_and_schema_contracts(monkeypatch):
    monkeypatch.setattr(database, "create_db_engine", lambda api_name: f"engine:{api_name}")
    monkeypatch.setattr(database, "create_session_factory", lambda api_name: f"factory:{api_name}")
    database.init("workflow-backend")
    assert database.get_engine() == "engine:workflow-backend"
    assert database.get_session_factory() == "factory:workflow-backend"

    assert workflow_schemas.WorkflowStepCreate(name="Step", step_type="agent").step_order == 0
    assert workflow_schemas.WorkflowCreate(name="Flow").level == "company"
    assert workflow_schemas.WorkflowUpdate(name="Updated").name == "Updated"
    assert workflow_schemas.WorkflowRunRequest(input_data={"x": 1}).input_data == {"x": 1}
    assert workflow_routes._workflow_to_response(make_workflow(), [make_step()]).steps[0].id == "step-1"


def test_python_package_contract_loads_runtime_components():
    from workflow_backend_api import contract

    assert contract.OPERATIONAL_ENDPOINTS == (
        "/health",
        "/readiness",
        "/liveness",
        "/startup",
        "/metrics",
    )
    assert contract.load_app() is main.app
    assert contract.load_runtime_routes() == (workflow_routes,)
    assert contract.load_runtime_repository_classes() == (WorkflowRepository,)
    assert contract.load_runtime_entity_classes() == (
        Workflow,
        WorkflowStep,
        WorkflowExecution,
        WorkflowStepExecution,
    )
