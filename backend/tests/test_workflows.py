"""Tests for Workflow CRUD + Execution API."""


class TestWorkflowCRUD:
    """Test Workflow CRUD endpoints."""

    def test_create_workflow(self, client, auth_headers):
        response = client.post("/api/v1/workflows", json={
            "name": "Test Workflow",
            "description": "A test workflow",
            "level": "user",
            "trigger_type": "manual",
            "execution_mode": "suggest",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert data["level"] == "user"
        assert data["execution_mode"] == "suggest"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_workflow_with_steps(self, client, auth_headers):
        response = client.post("/api/v1/workflows", json={
            "name": "Workflow With Steps",
            "level": "company",
            "trigger_type": "event",
            "execution_mode": "approval",
            "steps": [
                {"name": "Step 1", "step_order": 0, "step_type": "trigger", "is_entry_point": True},
                {"name": "Step 2", "step_order": 1, "step_type": "action", "agent_node": "log_action"},
            ],
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert len(data["steps"]) == 2
        assert data["steps"][0]["name"] == "Step 1"
        assert data["steps"][0]["is_entry_point"] is True
        assert data["steps"][1]["step_type"] == "action"

    def test_list_workflows(self, client, auth_headers):
        client.post("/api/v1/workflows", json={
            "name": "ListTest", "level": "user",
        }, headers=auth_headers)
        response = client.get("/api/v1/workflows", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_workflows_filter_level(self, client, auth_headers):
        client.post("/api/v1/workflows", json={
            "name": "SystemWF", "level": "system",
        }, headers=auth_headers)
        response = client.get("/api/v1/workflows?level=system", headers=auth_headers)
        assert response.status_code == 200
        for wf in response.json()["items"]:
            assert wf["level"] == "system"

    def test_get_workflow(self, client, auth_headers):
        create = client.post("/api/v1/workflows", json={
            "name": "GetMe", "level": "user",
        }, headers=auth_headers)
        wf_id = create.json()["id"]
        response = client.get(f"/api/v1/workflows/{wf_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "GetMe"

    def test_get_workflow_404(self, client, auth_headers):
        response = client.get("/api/v1/workflows/fake-id", headers=auth_headers)
        assert response.status_code == 404

    def test_update_workflow(self, client, auth_headers):
        create = client.post("/api/v1/workflows", json={
            "name": "UpdateMe", "level": "user",
        }, headers=auth_headers)
        wf_id = create.json()["id"]
        response = client.patch(f"/api/v1/workflows/{wf_id}", json={
            "name": "UpdatedName",
            "execution_mode": "auto",
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "UpdatedName"
        assert response.json()["execution_mode"] == "auto"

    def test_update_system_workflow_blocked(self, client, auth_headers):
        """System workflows should not be modifiable."""
        create = client.post("/api/v1/workflows", json={
            "name": "SystemBlock", "level": "system",
        }, headers=auth_headers)
        wf_id = create.json()["id"]
        response = client.patch(f"/api/v1/workflows/{wf_id}", json={
            "name": "CantChangeThis",
        }, headers=auth_headers)
        assert response.status_code == 403

    def test_delete_workflow(self, client, auth_headers):
        create = client.post("/api/v1/workflows", json={
            "name": "DeleteMe", "level": "user",
        }, headers=auth_headers)
        wf_id = create.json()["id"]
        response = client.delete(f"/api/v1/workflows/{wf_id}", headers=auth_headers)
        assert response.status_code == 204
        # Verify soft-deleted
        get = client.get(f"/api/v1/workflows/{wf_id}", headers=auth_headers)
        assert get.status_code == 404

    def test_delete_system_workflow_blocked(self, client, auth_headers):
        create = client.post("/api/v1/workflows", json={
            "name": "SysNoDelete", "level": "system",
        }, headers=auth_headers)
        wf_id = create.json()["id"]
        response = client.delete(f"/api/v1/workflows/{wf_id}", headers=auth_headers)
        assert response.status_code == 403


class TestWorkflowSteps:
    """Test Workflow step management."""

    def test_add_step(self, client, auth_headers):
        wf = client.post("/api/v1/workflows", json={
            "name": "StepWF", "level": "user",
        }, headers=auth_headers)
        wf_id = wf.json()["id"]
        response = client.post(f"/api/v1/workflows/{wf_id}/steps", json={
            "name": "New Step",
            "step_order": 0,
            "step_type": "trigger",
            "is_entry_point": True,
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["name"] == "New Step"
        assert response.json()["step_type"] == "trigger"

    def test_update_step(self, client, auth_headers):
        wf = client.post("/api/v1/workflows", json={
            "name": "StepUpdateWF", "level": "user",
            "steps": [{"name": "OldStep", "step_order": 0, "step_type": "action", "is_entry_point": True}],
        }, headers=auth_headers)
        step_id = wf.json()["steps"][0]["id"]
        wf_id = wf.json()["id"]
        response = client.patch(f"/api/v1/workflows/{wf_id}/steps/{step_id}", json={
            "name": "RenamedStep",
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "RenamedStep"

    def test_delete_step(self, client, auth_headers):
        wf = client.post("/api/v1/workflows", json={
            "name": "StepDelWF", "level": "user",
            "steps": [{"name": "GoneSoon", "step_order": 0, "step_type": "action", "is_entry_point": True}],
        }, headers=auth_headers)
        step_id = wf.json()["steps"][0]["id"]
        wf_id = wf.json()["id"]
        response = client.delete(f"/api/v1/workflows/{wf_id}/steps/{step_id}", headers=auth_headers)
        assert response.status_code == 204


class TestWorkflowExecution:
    """Test Workflow execution."""

    def test_run_workflow_no_steps(self, client, auth_headers):
        """Running a workflow with no steps should fail."""
        wf = client.post("/api/v1/workflows", json={
            "name": "EmptyWF", "level": "user",
        }, headers=auth_headers)
        wf_id = wf.json()["id"]
        response = client.post(f"/api/v1/workflows/{wf_id}/run", json={}, headers=auth_headers)
        assert response.status_code == 400

    def test_run_workflow_with_steps(self, client, auth_headers):
        """Running a workflow with log_action steps should succeed."""
        wf = client.post("/api/v1/workflows", json={
            "name": "RunMe",
            "level": "user",
            "execution_mode": "suggest",
            "steps": [
                {"name": "Entry", "step_order": 0, "step_type": "action",
                 "agent_node": "log_action", "is_entry_point": True},
            ],
        }, headers=auth_headers)
        wf_id = wf.json()["id"]
        response = client.post(f"/api/v1/workflows/{wf_id}/run", json={
            "input_data": {"test": True},
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["steps_completed"] == 1
        assert data["steps_total"] == 1

    def test_list_executions(self, client, auth_headers):
        # Create + run a workflow
        wf = client.post("/api/v1/workflows", json={
            "name": "ExeListWF", "level": "user",
            "steps": [{"name": "S1", "step_order": 0, "step_type": "action",
                        "agent_node": "log_action", "is_entry_point": True}],
        }, headers=auth_headers)
        wf_id = wf.json()["id"]
        client.post(f"/api/v1/workflows/{wf_id}/run", json={}, headers=auth_headers)

        response = client.get(f"/api/v1/workflows/{wf_id}/executions", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_execution_detail(self, client, auth_headers):
        wf = client.post("/api/v1/workflows", json={
            "name": "DetailWF", "level": "user",
            "steps": [{"name": "S1", "step_order": 0, "step_type": "action",
                        "agent_node": "log_action", "is_entry_point": True}],
        }, headers=auth_headers)
        wf_id = wf.json()["id"]
        run = client.post(f"/api/v1/workflows/{wf_id}/run", json={}, headers=auth_headers)
        exe_id = run.json()["id"]

        response = client.get(f"/api/v1/workflows/{wf_id}/executions/{exe_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "execution" in data
        assert "steps" in data
        assert len(data["steps"]) == 1
        assert data["steps"][0]["status"] == "completed"

    def test_run_inactive_workflow(self, client, auth_headers):
        """Running an inactive workflow should fail."""
        wf = client.post("/api/v1/workflows", json={
            "name": "InactiveWF", "level": "user",
            "steps": [{"name": "S1", "step_order": 0, "step_type": "action",
                        "agent_node": "log_action", "is_entry_point": True}],
        }, headers=auth_headers)
        wf_id = wf.json()["id"]
        # Deactivate
        client.patch(f"/api/v1/workflows/{wf_id}", json={"is_active": False}, headers=auth_headers)
        response = client.post(f"/api/v1/workflows/{wf_id}/run", json={}, headers=auth_headers)
        assert response.status_code == 400
