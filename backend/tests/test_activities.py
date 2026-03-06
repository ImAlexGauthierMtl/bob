"""Tests for Activity CRUD API."""


class TestActivityCRUD:
    """Test Activity CRUD endpoints."""

    def test_create_activity(self, client, auth_headers):
        response = client.post("/api/v1/activities", json={
            "subject": "Follow up call",
            "activity_type": "CALL",
            "priority": "HIGH",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["subject"] == "Follow up call"
        assert data["activity_type"] == "CALL"

    def test_list_activities(self, client, auth_headers):
        response = client.get("/api/v1/activities", headers=auth_headers)
        assert response.status_code == 200
        assert "items" in response.json()

    def test_get_activity(self, client, auth_headers):
        create = client.post("/api/v1/activities", json={"subject": "GetAct"}, headers=auth_headers)
        act_id = create.json()["id"]
        response = client.get(f"/api/v1/activities/{act_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_get_activity_404(self, client, auth_headers):
        response = client.get("/api/v1/activities/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_update_activity_status(self, client, auth_headers):
        create = client.post("/api/v1/activities", json={"subject": "Complete me"}, headers=auth_headers)
        act_id = create.json()["id"]
        response = client.patch(f"/api/v1/activities/{act_id}", json={"status": "COMPLETED"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED"

    def test_delete_activity(self, client, auth_headers):
        create = client.post("/api/v1/activities", json={"subject": "DelAct"}, headers=auth_headers)
        act_id = create.json()["id"]
        response = client.delete(f"/api/v1/activities/{act_id}", headers=auth_headers)
        assert response.status_code == 204
