"""Tests for Department CRUD API."""


class TestDepartmentCRUD:
    """Test Department CRUD endpoints."""

    def test_create_department(self, client, auth_headers):
        response = client.post("/api/v1/departments", json={
            "name": "Engineering",
            "description": "Product engineering team",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering"
        assert data["description"] == "Product engineering team"
        assert "id" in data

    def test_list_departments(self, client, auth_headers):
        client.post("/api/v1/departments", json={"name": "DeptList1"}, headers=auth_headers)
        response = client.get("/api/v1/departments", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    def test_get_department(self, client, auth_headers):
        create = client.post("/api/v1/departments", json={"name": "GetDept"}, headers=auth_headers)
        dept_id = create.json()["id"]
        response = client.get(f"/api/v1/departments/{dept_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "GetDept"

    def test_get_department_404(self, client, auth_headers):
        response = client.get("/api/v1/departments/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_update_department(self, client, auth_headers):
        create = client.post("/api/v1/departments", json={"name": "OldName"}, headers=auth_headers)
        dept_id = create.json()["id"]
        response = client.patch(f"/api/v1/departments/{dept_id}", json={
            "name": "NewName",
            "description": "Updated desc",
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "NewName"
        assert response.json()["description"] == "Updated desc"

    def test_delete_department(self, client, auth_headers):
        create = client.post("/api/v1/departments", json={"name": "DelDept"}, headers=auth_headers)
        dept_id = create.json()["id"]
        response = client.delete(f"/api/v1/departments/{dept_id}", headers=auth_headers)
        assert response.status_code == 204
        # Verify soft-deleted — GET should return 404
        get = client.get(f"/api/v1/departments/{dept_id}", headers=auth_headers)
        assert get.status_code == 404


class TestDepartmentMembers:
    """Test Department member management."""

    def test_add_member(self, client, auth_headers):
        # Create a dept
        dept = client.post("/api/v1/departments", json={"name": "MemberTestDept"}, headers=auth_headers)
        dept_id = dept.json()["id"]

        # Get current user ID via /me or register response
        me = client.get("/api/v1/capabilities/me", headers=auth_headers)
        if me.status_code == 200:
            user_id = me.json()["user_id"]
            response = client.post(f"/api/v1/departments/{dept_id}/members", json={
                "user_id": user_id,
                "is_manager": False,
            }, headers=auth_headers)
            assert response.status_code == 201
            assert response.json()["user_id"] == user_id
            assert response.json()["department_id"] == dept_id

    def test_add_member_to_nonexistent_dept(self, client, auth_headers):
        response = client.post("/api/v1/departments/fake-dept-id/members", json={
            "user_id": "some-user-id",
            "is_manager": False,
        }, headers=auth_headers)
        assert response.status_code == 404
