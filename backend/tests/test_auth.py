"""Tests for Auth API."""


class TestAuth:
    """Test authentication endpoints."""

    def test_register(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@crootest.com",
            "password": "StrongPass123!",
            "first_name": "New",
            "last_name": "User",
        })
        # 201 or 400 if user already exists
        assert response.status_code in [201, 400]

    def test_login(self, client):
        # Register first
        client.post("/api/v1/auth/register", json={
            "email": "login@crootest.com",
            "password": "LoginPass123!",
            "first_name": "Login",
            "last_name": "User",
        })
        response = client.post("/api/v1/auth/login", json={
            "email": "login@crootest.com",
            "password": "LoginPass123!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_wrong_password(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "login@crootest.com",
            "password": "WrongPassword!",
        })
        assert response.status_code in [401, 400]

    def test_me(self, client, auth_headers):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert "email" in response.json()

    def test_me_without_auth(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code in [401, 403]

    def test_health(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
