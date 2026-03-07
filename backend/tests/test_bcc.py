"""Tests for Bob's Control Center API."""


class TestBccRoles:
    """Test BCC role CRUD endpoints."""

    def test_list_roles(self, client, auth_headers):
        """GET /bcc/roles should return seeded roles."""
        response = client.get("/api/v1/bcc/roles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have the seeded Vendeur B2B role
        if len(data) > 0:
            role = data[0]
            assert "id" in role
            assert "name" in role
            assert "skill_count" in role
            assert "task_count" in role

    def test_create_role(self, client, auth_headers):
        """POST /bcc/roles should create a new role."""
        response = client.post("/api/v1/bcc/roles", json={
            "name": "Account Manager",
            "department": "Ventes",
            "description": "Gestion des comptes clients existants.",
            "icon": "fa-solid fa-user-tie",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Account Manager"
        assert data["department"] == "Ventes"

    def test_get_role_detail(self, client, auth_headers):
        """GET /bcc/roles/{id} should return role with skills, tasks, milestones."""
        # Get the seeded role first
        roles = client.get("/api/v1/bcc/roles", headers=auth_headers).json()
        if len(roles) > 0:
            role_id = roles[0]["id"]
            response = client.get(f"/api/v1/bcc/roles/{role_id}", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "skills" in data
            assert "tasks" in data
            assert "milestones" in data
            assert isinstance(data["skills"], list)
            assert isinstance(data["tasks"], list)

    def test_update_role(self, client, auth_headers):
        """PUT /bcc/roles/{id} should update a role."""
        # Create a role to update
        created = client.post("/api/v1/bcc/roles", json={
            "name": "Test Role",
            "department": "Test",
        }, headers=auth_headers).json()

        response = client.put(f"/api/v1/bcc/roles/{created['id']}", json={
            "name": "Updated Role",
            "description": "Updated description",
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Role"

    def test_delete_role(self, client, auth_headers):
        """DELETE /bcc/roles/{id} should delete a role."""
        # Create a role to delete
        created = client.post("/api/v1/bcc/roles", json={
            "name": "To Delete",
        }, headers=auth_headers).json()

        response = client.delete(f"/api/v1/bcc/roles/{created['id']}", headers=auth_headers)
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(f"/api/v1/bcc/roles/{created['id']}", headers=auth_headers)
        assert response.status_code == 404

    def test_get_nonexistent_role(self, client, auth_headers):
        """GET /bcc/roles/{id} with fake ID should return 404."""
        response = client.get("/api/v1/bcc/roles/fake-role-id", headers=auth_headers)
        assert response.status_code == 404


class TestBccSkills:
    """Test BCC skill endpoints."""

    def _get_role_id(self, client, auth_headers):
        """Helper: get first role ID."""
        roles = client.get("/api/v1/bcc/roles", headers=auth_headers).json()
        return roles[0]["id"] if roles else None

    def test_add_skill_to_role(self, client, auth_headers):
        """POST /bcc/roles/{id}/skills should add a skill."""
        role_id = self._get_role_id(client, auth_headers)
        if role_id:
            response = client.post(f"/api/v1/bcc/roles/{role_id}/skills", json={
                "name": "Test Skill",
                "type": "hard",
                "stage": "foundation",
                "priority": 3,
                "description": "A test skill.",
            }, headers=auth_headers)
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Test Skill"
            assert data["type"] == "hard"
            assert data["stage"] == "foundation"

    def test_add_skill_to_nonexistent_role(self, client, auth_headers):
        """POST /bcc/roles/{fake}/skills should return 404."""
        response = client.post("/api/v1/bcc/roles/fake-id/skills", json={
            "name": "Test",
        }, headers=auth_headers)
        assert response.status_code == 404


class TestBccTasks:
    """Test BCC task endpoints."""

    def _get_role_id(self, client, auth_headers):
        roles = client.get("/api/v1/bcc/roles", headers=auth_headers).json()
        return roles[0]["id"] if roles else None

    def test_add_task_to_role(self, client, auth_headers):
        """POST /bcc/roles/{id}/tasks should add a task."""
        role_id = self._get_role_id(client, auth_headers)
        if role_id:
            response = client.post(f"/api/v1/bcc/roles/{role_id}/tasks", json={
                "name": "Test Task",
                "frequency": "daily",
                "stage": "onboarding",
                "category": "test",
            }, headers=auth_headers)
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Test Task"
            assert data["frequency"] == "daily"

    def test_add_step_to_task(self, client, auth_headers):
        """POST /bcc/tasks/{id}/steps should add a step."""
        role_id = self._get_role_id(client, auth_headers)
        if role_id:
            # Create a task first
            task = client.post(f"/api/v1/bcc/roles/{role_id}/tasks", json={
                "name": "Step Test Task",
                "frequency": "weekly",
            }, headers=auth_headers).json()

            response = client.post(f"/api/v1/bcc/tasks/{task['id']}/steps", json={
                "step_number": 1,
                "instruction": "Do the first thing",
                "details": "More details here",
            }, headers=auth_headers)
            assert response.status_code == 201
            data = response.json()
            assert data["step_number"] == 1
            assert data["instruction"] == "Do the first thing"


class TestBccResources:
    """Test BCC resource endpoints."""

    def test_add_resource_to_skill(self, client, auth_headers):
        """POST /bcc/skills/{id}/resources should add a resource."""
        # Get a role, then get its first skill
        roles = client.get("/api/v1/bcc/roles", headers=auth_headers).json()
        if roles:
            detail = client.get(f"/api/v1/bcc/roles/{roles[0]['id']}", headers=auth_headers).json()
            if detail["skills"]:
                skill_id = detail["skills"][0]["id"]
                response = client.post(f"/api/v1/bcc/skills/{skill_id}/resources", json={
                    "title": "Test Resource",
                    "type": "article",
                    "content": "Some learning content.",
                }, headers=auth_headers)
                assert response.status_code == 201
                data = response.json()
                assert data["title"] == "Test Resource"
                assert data["type"] == "article"


class TestBccMilestones:
    """Test BCC milestone endpoints."""

    def test_add_milestone_to_role(self, client, auth_headers):
        """POST /bcc/roles/{id}/milestones should add a milestone."""
        roles = client.get("/api/v1/bcc/roles", headers=auth_headers).json()
        if roles:
            response = client.post(f"/api/v1/bcc/roles/{roles[0]['id']}/milestones", json={
                "name": "Test Milestone",
                "stage": "onboarding",
                "sort_order": 99,
                "criteria": {"test": True},
            }, headers=auth_headers)
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Test Milestone"
            assert data["stage"] == "onboarding"
