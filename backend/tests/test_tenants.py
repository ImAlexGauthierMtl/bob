"""Tests for Tenant admin CRUD API."""


class TestTenantCRUD:
    """Test Tenant CRUD endpoints — super_admin only."""

    def _make_super_admin(self, client, auth_headers, db):
        """Promote the test user to super_admin."""
        from app.domain.entities.user import User

        # Get current user email from token
        resp = client.get("/api/v1/users/me", headers=auth_headers)
        user_id = resp.json()["id"]

        user = db.query(User).filter(User.id == user_id).first()
        user.is_super_admin = True
        db.commit()

    def test_create_tenant(self, client, auth_headers, db):
        self._make_super_admin(client, auth_headers, db)
        response = client.post("/api/v1/admin/tenants", json={
            "name": "Test Tenant Corp",
            "slug": "test-tenant-corp",
            "owner_email": "owner@test-tenant.com",
            "owner_name": "Jane Owner",
            "plan": "STARTER",
            "max_users": 10,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Tenant Corp"
        assert data["slug"] == "test-tenant-corp"
        assert data["status"] == "TRIAL"
        assert data["plan"] == "STARTER"
        assert data["max_users"] == 10
        assert data["id"] is not None

    def test_create_duplicate_slug(self, client, auth_headers, db):
        self._make_super_admin(client, auth_headers, db)
        client.post("/api/v1/admin/tenants", json={
            "name": "First",
            "slug": "unique-slug",
            "owner_email": "a@b.com",
            "owner_name": "A B",
        }, headers=auth_headers)
        response = client.post("/api/v1/admin/tenants", json={
            "name": "Second",
            "slug": "unique-slug",
            "owner_email": "c@d.com",
            "owner_name": "C D",
        }, headers=auth_headers)
        assert response.status_code == 409

    def test_list_tenants(self, client, auth_headers, db):
        self._make_super_admin(client, auth_headers, db)
        response = client.get("/api/v1/admin/tenants", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_tenant(self, client, auth_headers, db):
        self._make_super_admin(client, auth_headers, db)
        create = client.post("/api/v1/admin/tenants", json={
            "name": "GetTest Tenant",
            "slug": "gettest-tenant",
            "owner_email": "get@test.com",
            "owner_name": "Get Test",
        }, headers=auth_headers)
        tenant_id = create.json()["id"]
        response = client.get(f"/api/v1/admin/tenants/{tenant_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "GetTest Tenant"

    def test_get_tenant_404(self, client, auth_headers, db):
        self._make_super_admin(client, auth_headers, db)
        response = client.get("/api/v1/admin/tenants/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404

    def test_update_tenant(self, client, auth_headers, db):
        self._make_super_admin(client, auth_headers, db)
        create = client.post("/api/v1/admin/tenants", json={
            "name": "UpdateTest",
            "slug": "updatetest",
            "owner_email": "u@t.com",
            "owner_name": "U T",
        }, headers=auth_headers)
        tenant_id = create.json()["id"]
        response = client.patch(f"/api/v1/admin/tenants/{tenant_id}", json={
            "plan": "PRO",
            "max_users": 20,
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["plan"] == "PRO"
        assert response.json()["max_users"] == 20

    def test_delete_tenant(self, client, auth_headers, db):
        self._make_super_admin(client, auth_headers, db)
        create = client.post("/api/v1/admin/tenants", json={
            "name": "DeleteTest",
            "slug": "deletetest",
            "owner_email": "d@t.com",
            "owner_name": "D T",
        }, headers=auth_headers)
        tenant_id = create.json()["id"]
        response = client.delete(f"/api/v1/admin/tenants/{tenant_id}", headers=auth_headers)
        assert response.status_code == 204
        get_resp = client.get(f"/api/v1/admin/tenants/{tenant_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_provision_tenant(self, client, auth_headers, db):
        self._make_super_admin(client, auth_headers, db)
        create = client.post("/api/v1/admin/tenants", json={
            "name": "ProvisionTest",
            "slug": "provisiontest",
            "owner_email": "p@t.com",
            "owner_name": "P T",
        }, headers=auth_headers)
        tenant_id = create.json()["id"]
        response = client.post(f"/api/v1/admin/tenants/{tenant_id}/provision", json={
            "admin_email": "admin@provisiontest.com",
            "admin_password": "Secure123!",
            "admin_first_name": "Admin",
            "admin_last_name": "Provision",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["admin_email"] == "admin@provisiontest.com"
        assert data["tenant_id"] == tenant_id

    def test_create_without_auth(self, client):
        response = client.post("/api/v1/admin/tenants", json={
            "name": "NoAuth",
            "slug": "noauth",
            "owner_email": "na@test.com",
            "owner_name": "No Auth",
        })
        assert response.status_code in [401, 403]

    def test_create_without_super_admin(self, client, auth_headers):
        """Regular user should be denied (403)."""
        response = client.post("/api/v1/admin/tenants", json={
            "name": "Denied",
            "slug": "denied",
            "owner_email": "d@test.com",
            "owner_name": "Denied",
        }, headers=auth_headers)
        assert response.status_code == 403
