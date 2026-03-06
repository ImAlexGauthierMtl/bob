"""Tests for Organization CRUD API."""


class TestOrganizationCRUD:
    """Test Organization CRUD endpoints."""

    def test_create_organization(self, client, auth_headers):
        response = client.post("/api/v1/organizations", json={
            "name": "Test Corp",
            "industry": "Technology",
            "status": "PROSPECT",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Corp"
        assert data["industry"] == "Technology"
        assert data["id"] is not None

    def test_list_organizations(self, client, auth_headers):
        response = client.get("/api/v1/organizations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_organization(self, client, auth_headers):
        # Create first
        create = client.post("/api/v1/organizations", json={"name": "GetTest Corp"}, headers=auth_headers)
        org_id = create.json()["id"]
        # Get
        response = client.get(f"/api/v1/organizations/{org_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "GetTest Corp"

    def test_get_organization_404(self, client, auth_headers):
        response = client.get("/api/v1/organizations/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_update_organization(self, client, auth_headers):
        create = client.post("/api/v1/organizations", json={"name": "UpdateTest"}, headers=auth_headers)
        org_id = create.json()["id"]
        response = client.patch(f"/api/v1/organizations/{org_id}", json={"industry": "Finance"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["industry"] == "Finance"

    def test_delete_organization(self, client, auth_headers):
        create = client.post("/api/v1/organizations", json={"name": "DeleteTest"}, headers=auth_headers)
        org_id = create.json()["id"]
        response = client.delete(f"/api/v1/organizations/{org_id}", headers=auth_headers)
        assert response.status_code == 204
        # Verify soft deleted (GET returns 404)
        get_resp = client.get(f"/api/v1/organizations/{org_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_create_without_auth(self, client):
        response = client.post("/api/v1/organizations", json={"name": "NoAuth"})
        assert response.status_code in [401, 403]
