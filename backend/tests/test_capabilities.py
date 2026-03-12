"""Tests for Capability API."""


class TestCapabilityCatalog:
    """Test Capability catalog endpoints."""

    def test_list_catalog(self, client, auth_headers):
        """Catalog should return seeded capabilities."""
        response = client.get("/api/v1/capabilities/catalog", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should have capabilities from seed
        if len(data) > 0:
            cap = data[0]
            assert "code" in cap
            assert "scope" in cap
            assert "risk_level" in cap


class TestUserCapabilities:
    """Test user-level capability operations."""

    def test_get_my_capabilities(self, client, auth_headers):
        """GET /capabilities/me should return resolved capabilities + agent mode."""
        response = client.get("/api/v1/capabilities/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "agent_mode" in data
        assert "trust_score" in data
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)
        # Default trust_score is 0.1 → agent_mode should be "suggest"
        assert data["agent_mode"] == "suggest"
        assert data["trust_score"] == 0.1

    def test_assign_capability(self, client, auth_headers):
        """Assign a capability to a user."""
        # Get user_id first
        me = client.get("/api/v1/capabilities/me", headers=auth_headers)
        user_id = me.json()["user_id"]

        # Get a valid capability code from catalog
        catalog = client.get("/api/v1/capabilities/catalog", headers=auth_headers)
        caps = catalog.json()
        if len(caps) > 0:
            cap_code = caps[0]["code"]
            response = client.post(f"/api/v1/capabilities/users/{user_id}/assign", json={
                "capability_code": cap_code,
                "granted": True,
            }, headers=auth_headers)
            assert response.status_code == 201
            assert response.json()["capability"] == cap_code
            assert response.json()["granted"] is True

    def test_assign_invalid_capability(self, client, auth_headers):
        """Assigning non-existent capability should fail."""
        me = client.get("/api/v1/capabilities/me", headers=auth_headers)
        user_id = me.json()["user_id"]
        response = client.post(f"/api/v1/capabilities/users/{user_id}/assign", json={
            "capability_code": "totally.fake.capability",
            "granted": True,
        }, headers=auth_headers)
        assert response.status_code == 404

    def test_check_capability(self, client, auth_headers):
        """POST /capabilities/check should return granted status + agent_mode."""
        response = client.post("/api/v1/capabilities/check?capability_code=dashboard.view", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "capability" in data
        assert "granted" in data
        assert "agent_mode" in data
        assert "trust_score" in data

    def test_get_user_capabilities(self, client, auth_headers):
        """GET /capabilities/users/{id} should return resolved capabilities."""
        me = client.get("/api/v1/capabilities/me", headers=auth_headers)
        user_id = me.json()["user_id"]
        response = client.get(f"/api/v1/capabilities/users/{user_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert "agent_mode" in data

    def test_get_nonexistent_user_capabilities(self, client, auth_headers):
        response = client.get("/api/v1/capabilities/users/fake-user-id", headers=auth_headers)
        assert response.status_code == 404
