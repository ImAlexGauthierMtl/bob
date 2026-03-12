"""Tests for KB Article Workflow — multi-turn article creation flow.

Tests the workflow phases:
  1. Clarification (PAUSE)
  2. Plan validation (PAUSE)
  3. Content generation + Publication (COMPLETE)
"""

import pytest
from unittest.mock import patch, MagicMock


class TestKBArticleWorkflow:
    """Test the KB article creation workflow."""

    def _make_context(self, db, topic="créer un contact"):
        """Create a WorkflowContext for testing."""
        from app.agents.workflow_engine import WorkflowContext
        from app.agents.intent_classifier import ExtractedEntities

        entities = ExtractedEntities(kb_topic=topic)
        return WorkflowContext(
            db=db,
            tenant_id="default",
            user_id="test-user",
            user_email="test@croo.digital",
            entities=entities,
            user_message=f"Créer un article sur {topic}",
        )

    def test_phase1_clarification_pauses(self, db):
        """Phase 1 should pause and ask clarification questions."""
        from app.agents.generated.kb_article_workflow import create_kb_article_flow

        ctx = self._make_context(db)
        result = create_kb_article_flow(ctx)

        assert result.paused is True
        assert result.resume_key == "kb_clarification_done"
        assert "contact" in result.message.lower()
        assert ctx.state["topic"] == "créer un contact"

    def test_phase2_plan_proposal_pauses(self, db):
        """Phase 2 should propose a plan and pause for validation."""
        from app.agents.generated.kb_article_workflow import resume_kb_clarification

        ctx = self._make_context(db)
        ctx.state["topic"] = "créer un contact"
        ctx.user_message = "Le module contacts, pour tous les utilisateurs, ajouter un contact avec ses infos"

        result = resume_kb_clarification(ctx)

        assert result.paused is True
        assert result.resume_key == "kb_plan_approved"
        assert "plan" in result.message.lower() or "titre" in result.message.lower()
        assert ctx.state.get("title")
        assert ctx.state.get("plan")

    @patch("app.agents.kb_llm_client.generate_kb_content_sync")
    def test_phase3_generation_and_publication(self, mock_gen, client, auth_headers, db):
        """Phase 3 should generate content, create article, and complete."""
        mock_gen.return_value = """# Comment créer un contact

## Aperçu
Cette procédure explique comment ajouter un nouveau contact dans le CRM.

## Prérequis
- Accès au module Contacts
- Permissions de création

## Procédure étape par étape

### Étape 1 — Accéder au module Contacts
Cliquez sur le menu Contacts dans la barre latérale.
![Étape 1](screenshot_placeholder_1)

### Étape 2 — Cliquer sur le bouton Ajouter
Cliquez sur le bouton + en haut à droite.
![Étape 2](screenshot_placeholder_2)

## Résultat attendu
Le contact apparaît dans la liste des contacts.

## Conseils et bonnes pratiques
- Toujours remplir l'email
- Vérifier les doublons

## Articles reliés
- Comment créer une organisation
"""
        # Create a category first
        client.post("/api/v1/kb/categories", json={
            "name": "Sales & CRM", "slug": "sales-crm",
        }, headers=auth_headers)

        from app.agents.generated.kb_article_workflow import resume_kb_plan_approved
        from app.agents.workflow_engine import WorkflowContext
        from app.agents.intent_classifier import ExtractedEntities

        entities = ExtractedEntities(kb_topic="créer un contact")
        ctx = WorkflowContext(
            db=db,
            tenant_id="default",
            user_id="test-user",
            user_email="test@croo.digital",
            entities=entities,
            user_message="oui, valide le plan",
            state={
                "topic": "créer un contact",
                "title": "Comment créer un contact",
                "slug": "comment-creer-un-contact",
                "module": "Contacts",
                "audience": "Tous les utilisateurs",
                "scenario": "Ajouter un contact avec ses infos",
                "plan": "1. Accéder au module\n2. Cliquer sur Ajouter\n3. Remplir les champs",
            },
        )

        result = resume_kb_plan_approved(ctx)

        assert result.paused is False
        assert "publié" in result.message.lower() or "✅" in result.message
        mock_gen.assert_called_once()

    def test_phase3_rejection_loops_back(self, db):
        """Rejecting the plan should loop back to clarification."""
        from app.agents.generated.kb_article_workflow import resume_kb_plan_approved

        ctx = self._make_context(db)
        ctx.state["topic"] = "créer un contact"
        ctx.state["title"] = "Comment créer un contact"
        ctx.state["plan"] = "1. Step 1"
        ctx.user_message = "Non, modifie le plan s'il te plaît"

        result = resume_kb_plan_approved(ctx)

        assert result.paused is True
        assert result.resume_key == "kb_clarification_done"


class TestKBWorkflowHelpers:
    """Test helper functions from the workflow module."""

    def test_infer_module_contacts(self):
        from app.agents.generated.kb_article_workflow import _infer_module
        assert _infer_module("le module contacts") == "Contacts"

    def test_infer_module_organisations(self):
        from app.agents.generated.kb_article_workflow import _infer_module
        assert _infer_module("gestion des organisations") == "Organisations"

    def test_infer_module_default(self):
        from app.agents.generated.kb_article_workflow import _infer_module
        assert _infer_module("quelque chose de random") == "Général"

    def test_infer_audience_admin(self):
        from app.agents.generated.kb_article_workflow import _infer_audience
        assert _infer_audience("pour les administrateurs") == "Administrateurs"

    def test_infer_audience_default(self):
        from app.agents.generated.kb_article_workflow import _infer_audience
        assert _infer_audience("pour tout le monde") == "Tous les utilisateurs"

    def test_generate_title_cleanup(self):
        from app.agents.generated.kb_article_workflow import _generate_title
        title = _generate_title("comment créer un contact", "Contacts")
        assert title.startswith("Comment")
        assert "contact" in title.lower()

    def test_clean_generated_content(self):
        from app.agents.generated.kb_article_workflow import _clean_generated_content
        content = "```markdown\n# Title\nContent\n```"
        cleaned = _clean_generated_content(content)
        assert cleaned.startswith("# Title")
        assert "```" not in cleaned

    def test_extract_excerpt(self):
        from app.agents.generated.kb_article_workflow import _extract_excerpt
        content = "# Title\n\n## Aperçu\nCeci est un aperçu de la procédure.\n\n## Prérequis\n- Accès"
        excerpt = _extract_excerpt(content)
        assert "aperçu" in excerpt.lower()

    def test_infer_category_slug(self):
        from app.agents.generated.kb_article_workflow import _infer_category_slug
        assert _infer_category_slug("Contacts") == "sales-crm"
        assert _infer_category_slug("Bob AI") == "ai-features"
        assert _infer_category_slug("Paramètres") == "admin"

    def test_infer_tags(self):
        from app.agents.generated.kb_article_workflow import _infer_tags
        tags = _infer_tags("Contacts", "Tous les utilisateurs")
        assert "contacts" in tags
        assert "procédure" in tags
        assert len(tags) <= 5

    def test_estimate_read_time(self):
        from app.agents.generated.kb_article_workflow import _estimate_read_time
        short_content = "Some short content."
        assert _estimate_read_time(short_content) >= 3  # Minimum 3 min


class TestKBScreenshotService:
    """Test the screenshot service helper functions."""

    def test_replace_placeholders_with_urls(self):
        from app.agents.kb_screenshot_service import replace_screenshot_placeholders
        content = "Text\n![Step 1](screenshot_placeholder_1)\nMore text\n![Step 2](screenshot_placeholder_2)"
        urls = ["/static/kb/screenshots/abc_step_1.png", "/static/kb/screenshots/abc_step_2.png"]
        result = replace_screenshot_placeholders(content, urls)
        assert "/static/kb/screenshots/abc_step_1.png" in result
        assert "/static/kb/screenshots/abc_step_2.png" in result
        assert "screenshot_placeholder" not in result

    def test_replace_placeholders_with_missing_url(self):
        from app.agents.kb_screenshot_service import replace_screenshot_placeholders
        content = "Text\n![Step 1](screenshot_placeholder_1)\nMore text"
        urls = [""]  # No screenshot captured
        result = replace_screenshot_placeholders(content, urls)
        assert "screenshot_placeholder" not in result

    def test_replace_final_placeholder(self):
        from app.agents.kb_screenshot_service import replace_screenshot_placeholders
        content = "![Result](screenshot_placeholder_final)"
        urls = ["/static/kb/screenshots/abc_step_1.png"]
        result = replace_screenshot_placeholders(content, urls)
        assert "/static/kb/screenshots/abc_step_1.png" in result


class TestKBGenerationMission:
    """Test mission prompt generation."""

    def test_clarification_prompt_includes_topic(self):
        from app.agents.kb_generation_mission import get_kb_clarification_mission
        prompt = get_kb_clarification_mission("créer un contact")
        assert "créer un contact" in prompt
        assert "CLARIFICATION" in prompt

    def test_generation_prompt_includes_all_fields(self):
        from app.agents.kb_generation_mission import get_kb_generation_prompt
        prompt = get_kb_generation_prompt(
            title="Comment créer un contact",
            module="Contacts",
            audience="Tous",
            scenario="Ajouter un contact",
            plan="1. Étape 1\n2. Étape 2",
        )
        assert "Comment créer un contact" in prompt
        assert "Contacts" in prompt
        assert "Tous" in prompt
        assert "Étape 1" in prompt


class TestIntentClassifierKBArticle:
    """Test that create_kb_article intent is properly configured."""

    def test_create_kb_article_in_supported_intents(self):
        from app.agents.intent_classifier import SUPPORTED_INTENTS
        assert "create_kb_article" in SUPPORTED_INTENTS

    def test_kb_topic_entity_field_exists(self):
        from app.agents.intent_classifier import ExtractedEntities
        e = ExtractedEntities(kb_topic="test topic")
        assert e.kb_topic == "test topic"

    def test_kb_topic_default_none(self):
        from app.agents.intent_classifier import ExtractedEntities
        e = ExtractedEntities()
        assert e.kb_topic is None
