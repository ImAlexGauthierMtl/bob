"""Tests for Opportunity CRUD API."""


class TestOpportunityCRUD:
    """Test Opportunity CRUD endpoints."""

    def test_create_opportunity(self, client, auth_headers):
        response = client.post("/api/v1/opportunities", json={
            "name": "Big Deal",
            "stage": "PROSPECTING",
            "amount": 50000,
            "probability": 30,
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Big Deal"
        assert data["amount"] == 50000

    def test_list_opportunities(self, client, auth_headers):
        response = client.get("/api/v1/opportunities", headers=auth_headers)
        assert response.status_code == 200
        assert "items" in response.json()

    def test_get_opportunity(self, client, auth_headers):
        create = client.post("/api/v1/opportunities", json={"name": "GetOpp"}, headers=auth_headers)
        opp_id = create.json()["id"]
        response = client.get(f"/api/v1/opportunities/{opp_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_get_opportunity_404(self, client, auth_headers):
        response = client.get("/api/v1/opportunities/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_update_opportunity_stage(self, client, auth_headers):
        create = client.post("/api/v1/opportunities", json={"name": "StageOpp"}, headers=auth_headers)
        opp_id = create.json()["id"]
        response = client.patch(f"/api/v1/opportunities/{opp_id}", json={"stage": "NEGOTIATION"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["stage"] == "NEGOTIATION"

    def test_delete_opportunity(self, client, auth_headers):
        create = client.post("/api/v1/opportunities", json={"name": "DelOpp"}, headers=auth_headers)
        opp_id = create.json()["id"]
        response = client.delete(f"/api/v1/opportunities/{opp_id}", headers=auth_headers)
        assert response.status_code == 204
