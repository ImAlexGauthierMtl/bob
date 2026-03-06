"""Tests for Quote CRUD API."""


class TestQuoteCRUD:
    """Test Quote CRUD endpoints."""

    def test_create_quote(self, client, auth_headers):
        response = client.post("/api/v1/quotes", json={
            "name": "Q-2026-001",
            "subtotal": 10000,
            "tax_percent": 14.975,
            "total": 11497.50,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Q-2026-001"
        assert data["total"] == 11497.50

    def test_list_quotes(self, client, auth_headers):
        response = client.get("/api/v1/quotes", headers=auth_headers)
        assert response.status_code == 200
        assert "items" in response.json()

    def test_get_quote(self, client, auth_headers):
        create = client.post("/api/v1/quotes", json={"name": "GetQuote"}, headers=auth_headers)
        quote_id = create.json()["id"]
        response = client.get(f"/api/v1/quotes/{quote_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_get_quote_404(self, client, auth_headers):
        response = client.get("/api/v1/quotes/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_update_quote_status(self, client, auth_headers):
        create = client.post("/api/v1/quotes", json={"name": "StatusQuote"}, headers=auth_headers)
        quote_id = create.json()["id"]
        response = client.patch(f"/api/v1/quotes/{quote_id}", json={"status": "SENT"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "SENT"

    def test_delete_quote(self, client, auth_headers):
        create = client.post("/api/v1/quotes", json={"name": "DelQuote"}, headers=auth_headers)
        quote_id = create.json()["id"]
        response = client.delete(f"/api/v1/quotes/{quote_id}", headers=auth_headers)
        assert response.status_code == 204
