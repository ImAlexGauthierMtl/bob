"""Tests for Contact CRUD API."""


class TestContactCRUD:
    """Test Contact CRUD endpoints."""

    def test_create_contact(self, client, auth_headers):
        response = client.post("/api/v1/contacts", json={
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@crootest.com",
            "job_title": "CEO",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["email"] == "john@crootest.com"

    def test_list_contacts(self, client, auth_headers):
        response = client.get("/api/v1/contacts", headers=auth_headers)
        assert response.status_code == 200
        assert "items" in response.json()
        assert "total" in response.json()

    def test_get_contact(self, client, auth_headers):
        create = client.post("/api/v1/contacts", json={"first_name": "Jane", "last_name": "Get"}, headers=auth_headers)
        contact_id = create.json()["id"]
        response = client.get(f"/api/v1/contacts/{contact_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["first_name"] == "Jane"

    def test_get_contact_404(self, client, auth_headers):
        response = client.get("/api/v1/contacts/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_update_contact(self, client, auth_headers):
        create = client.post("/api/v1/contacts", json={"first_name": "Up", "last_name": "Date"}, headers=auth_headers)
        contact_id = create.json()["id"]
        response = client.patch(f"/api/v1/contacts/{contact_id}", json={"job_title": "CTO"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["job_title"] == "CTO"

    def test_delete_contact(self, client, auth_headers):
        create = client.post("/api/v1/contacts", json={"first_name": "Del", "last_name": "Ete"}, headers=auth_headers)
        contact_id = create.json()["id"]
        response = client.delete(f"/api/v1/contacts/{contact_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_contact_with_organization(self, client, auth_headers):
        org = client.post("/api/v1/organizations", json={"name": "ContactOrg"}, headers=auth_headers)
        org_id = org.json()["id"]
        response = client.post("/api/v1/contacts", json={
            "first_name": "Linked",
            "last_name": "Contact",
            "organization_id": org_id,
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["organization_id"] == org_id
