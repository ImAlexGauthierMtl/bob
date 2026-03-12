"""Tests for Knowledge Base API."""

import pytest


class TestKBCategories:
    """Test KB category endpoints."""

    def test_create_category(self, client, auth_headers):
        resp = client.post("/api/v1/kb/categories", json={
            "name": "Getting Started",
            "slug": "getting-started",
            "description": "Essential guides for new users",
            "icon": "fa-solid fa-rocket",
            "color": "#3b82f6",
            "sort_order": 0,
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Getting Started"
        assert data["slug"] == "getting-started"
        assert data["article_count"] == 0

    def test_list_categories(self, client, auth_headers):
        # Create 2 categories
        client.post("/api/v1/kb/categories", json={
            "name": "Sales & CRM", "slug": "sales-crm",
        }, headers=auth_headers)
        client.post("/api/v1/kb/categories", json={
            "name": "AI Features", "slug": "ai-features",
        }, headers=auth_headers)
        resp = client.get("/api/v1/kb/categories", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    def test_list_categories_requires_auth(self, client):
        resp = client.get("/api/v1/kb/categories")
        assert resp.status_code == 401


class TestKBArticles:
    """Test KB article endpoints."""

    @pytest.fixture
    def category_id(self, client, auth_headers):
        resp = client.post("/api/v1/kb/categories", json={
            "name": "Test Category", "slug": "test-cat",
        }, headers=auth_headers)
        return resp.json()["id"]

    def test_create_article(self, client, auth_headers, category_id):
        resp = client.post("/api/v1/kb/articles", json={
            "title": "How to Create Contacts",
            "slug": "how-to-create-contacts",
            "excerpt": "Learn how to add and manage contacts",
            "content": "# Creating Contacts\n\nThis guide shows you...",
            "category_id": category_id,
            "visibility": "shared",
            "required_module": "contacts",
            "author_name": "Bob AI",
            "author_role": "AI Assistant",
            "read_time_minutes": 5,
            "is_published": True,
            "tags": ["contacts", "getting-started"],
        }, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "How to Create Contacts"
        assert data["visibility"] == "shared"
        assert data["is_published"] is True
        assert data["tags"] == ["contacts", "getting-started"]

    def test_get_article_by_slug(self, client, auth_headers, category_id):
        client.post("/api/v1/kb/articles", json={
            "title": "Slug Test Article",
            "slug": "slug-test-article",
            "content": "Content here",
            "is_published": True,
        }, headers=auth_headers)
        resp = client.get("/api/v1/kb/articles/slug-test-article", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Slug Test Article"
        assert data["view_count"] >= 1  # Auto-incremented

    def test_get_article_not_found(self, client, auth_headers):
        resp = client.get("/api/v1/kb/articles/nonexistent-slug", headers=auth_headers)
        assert resp.status_code == 404

    def test_list_articles(self, client, auth_headers, category_id):
        # Create published article
        client.post("/api/v1/kb/articles", json={
            "title": "List Test 1", "slug": "list-test-1",
            "content": "c", "is_published": True, "category_id": category_id,
        }, headers=auth_headers)
        resp = client.get("/api/v1/kb/articles", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_articles_filter_category(self, client, auth_headers, category_id):
        client.post("/api/v1/kb/articles", json={
            "title": "Cat Filter", "slug": "cat-filter",
            "content": "c", "is_published": True, "category_id": category_id,
        }, headers=auth_headers)
        resp = client.get(f"/api/v1/kb/articles?category_id={category_id}", headers=auth_headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["category_id"] == category_id

    def test_list_articles_search(self, client, auth_headers):
        client.post("/api/v1/kb/articles", json={
            "title": "Unique Search Alpha", "slug": "unique-search-alpha",
            "content": "c", "is_published": True,
        }, headers=auth_headers)
        resp = client.get("/api/v1/kb/articles?search=Unique+Search+Alpha", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    def test_update_article(self, client, auth_headers):
        create = client.post("/api/v1/kb/articles", json={
            "title": "Update Me", "slug": "update-me", "content": "old", "is_published": True,
        }, headers=auth_headers)
        article_id = create.json()["id"]
        resp = client.patch(f"/api/v1/kb/articles/{article_id}", json={
            "title": "Updated Title", "content": "new content",
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_delete_article(self, client, auth_headers):
        create = client.post("/api/v1/kb/articles", json={
            "title": "Delete Me", "slug": "delete-me", "content": "x", "is_published": True,
        }, headers=auth_headers)
        article_id = create.json()["id"]
        resp = client.delete(f"/api/v1/kb/articles/{article_id}", headers=auth_headers)
        assert resp.status_code == 204
        # Verify it's gone
        resp = client.get("/api/v1/kb/articles/delete-me", headers=auth_headers)
        assert resp.status_code == 404

    def test_popular_articles(self, client, auth_headers):
        client.post("/api/v1/kb/articles", json={
            "title": "Popular One", "slug": "popular-one", "content": "c", "is_published": True,
        }, headers=auth_headers)
        # View it multiple times
        for _ in range(3):
            client.get("/api/v1/kb/articles/popular-one", headers=auth_headers)
        resp = client.get("/api/v1/kb/articles/popular?limit=5", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


class TestKBFeedback:
    """Test article feedback."""

    def test_feedback_helpful(self, client, auth_headers):
        create = client.post("/api/v1/kb/articles", json={
            "title": "Feedback Test", "slug": "feedback-test", "content": "c", "is_published": True,
        }, headers=auth_headers)
        article_id = create.json()["id"]
        resp = client.post(f"/api/v1/kb/articles/{article_id}/feedback", json={
            "helpful": True,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["helpful_yes"] >= 1

    def test_feedback_not_helpful(self, client, auth_headers):
        create = client.post("/api/v1/kb/articles", json={
            "title": "Feedback No", "slug": "feedback-no", "content": "c", "is_published": True,
        }, headers=auth_headers)
        article_id = create.json()["id"]
        resp = client.post(f"/api/v1/kb/articles/{article_id}/feedback", json={
            "helpful": False,
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["helpful_no"] >= 1


class TestKBStats:
    """Test KB statistics endpoint."""

    def test_get_stats(self, client, auth_headers):
        resp = client.get("/api/v1/kb/stats", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_articles" in data
        assert "published_articles" in data
        assert "total_categories" in data
        assert "total_views" in data
        assert "avg_helpfulness" in data

    def test_stats_requires_auth(self, client):
        resp = client.get("/api/v1/kb/stats")
        assert resp.status_code == 401
