"""KB Article Workflow — auto-loaded by workflow_engine.load_generated_workflows().

Multi-turn workflow for creating Knowledge Base articles:
  1. Clarification (PAUSE) — Bob asks about topic, module, audience
  2. Plan validation (PAUSE) — Bob proposes article outline
  3. Generation (LLM) — Kimi K2.5 generates full markdown content
  4. Screenshots (Playwright) — optional step captures
  5. Publication (KB API) — article created and published
  6. Return link to user
"""

import re
import structlog
from slugify import slugify

from app.agents.workflow_engine import workflow, resume_handler, WorkflowContext, WorkflowResult
from app.agents.kb_generation_mission import (
    KB_GENERATION_SYSTEM_PROMPT,
    get_kb_generation_prompt,
)

logger = structlog.get_logger(__name__)


def _slugify_title(title: str) -> str:
    """Generate a URL-safe slug from article title."""
    try:
        return slugify(title, max_length=200)
    except Exception:
        # Fallback if python-slugify not available
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        return slug[:200]


def _estimate_read_time(content: str) -> int:
    """Estimate read time in minutes (avg 200 words/min for technical docs)."""
    word_count = len(content.split())
    return max(3, round(word_count / 200))


# ═══════════════════════════════════════════════════════════════
#  WORKFLOW: create_kb_article
#  Triggered by: "créer un article KB", "nouvelle procédure", etc.
# ═══════════════════════════════════════════════════════════════

@workflow("create_kb_article")
def create_kb_article_flow(ctx: WorkflowContext) -> WorkflowResult:
    """Phase 1 — Ask clarification questions about the KB article."""

    topic = ctx.entities.kb_topic or ctx.user_message
    ctx.state["topic"] = topic

    # Build clarification question
    ctx.add_tool_step("analyze request")

    questions = (
        f"📝 Parfait, je vais créer un article de base de connaissances sur **{topic}**.\n\n"
        "Pour bien rédiger cet article, j'ai quelques questions :\n\n"
        "1. **Module concerné** — Quel module ou fonctionnalité du CRM est impliqué ?\n"
        "   _(contacts, organisations, opportunités, catalogue, activités, paramètres...)_\n\n"
        "2. **Public cible** — Pour qui est cet article ?\n"
        "   _(administrateur, gestionnaire, utilisateur standard, tous)_\n\n"
        "3. **Scénario** — Peux-tu me décrire brièvement le scénario d'utilisation ?\n"
        "   _(ex: « L'utilisateur veut ajouter un contact avec son organisation »)_\n\n"
        "Réponds à ces questions et je te proposerai un plan d'article. 📋"
    )

    return ctx.pause(
        message=questions,
        resume_key="kb_clarification_done",
    )


@resume_handler("kb_clarification_done")
def resume_kb_clarification(ctx: WorkflowContext) -> WorkflowResult:
    """Phase 2 — Parse answers and propose an article plan."""

    user_response = ctx.user_message
    topic = ctx.state.get("topic", "")

    # Store the clarification answers
    ctx.state["clarification"] = user_response

    # Try to infer module, audience, scenario from the response
    # These will be refined by the LLM during generation
    module = _infer_module(user_response)
    audience = _infer_audience(user_response)

    ctx.state["module"] = module
    ctx.state["audience"] = audience
    ctx.state["scenario"] = user_response

    # Generate a title
    title = _generate_title(topic, module)
    ctx.state["title"] = title
    slug = _slugify_title(title)
    ctx.state["slug"] = slug

    # Propose a plan based on the topic
    plan = _generate_plan(topic, module, user_response)
    ctx.state["plan"] = plan

    ctx.add_tool_step("generate plan")

    plan_message = (
        f"Voici le plan que je propose pour l'article :\n\n"
        f"📝 **Titre** : {title}\n"
        f"📂 **Module** : {module}\n"
        f"👥 **Public** : {audience}\n"
        f"⏱️ **Temps de lecture estimé** : 5-8 min\n\n"
        f"**Plan des étapes :**\n{plan}\n\n"
        "---\n\n"
        "✅ **Valide ce plan** et je vais :\n"
        "1. Rédiger le contenu complet de l'article\n"
        "2. Publier l'article dans la base de connaissances\n"
        "3. Te retourner le lien\n\n"
        "Tu peux aussi me demander des modifications au plan. 📋"
    )

    return ctx.pause(
        message=plan_message,
        resume_key="kb_plan_approved",
    )


@resume_handler("kb_plan_approved")
def resume_kb_plan_approved(ctx: WorkflowContext) -> WorkflowResult:
    """Phase 3 — Generate content, create article, return link."""

    user_response = ctx.user_message.strip().lower()

    # Check if user wants modifications
    rejection_keywords = ["non", "modifie", "change", "pas", "no", "adjust", "corrige"]
    if any(kw in user_response for kw in rejection_keywords) and \
       not any(kw in user_response for kw in ["ok", "oui", "go", "parfait", "valide", "yes"]):
        # User wants changes — update plan and re-ask
        ctx.state["plan_feedback"] = ctx.user_message
        ctx.add_tool_step("revise plan")

        return ctx.pause(
            message=(
                "D'accord, peux-tu me préciser les modifications que tu souhaites "
                "apporter au plan ? Je vais l'ajuster et te le reproposer."
            ),
            resume_key="kb_clarification_done",
        )

    # User approved — generate content
    ctx.add_tool_step("generate content (Kimi K2.5)")

    title = ctx.state.get("title", "")
    module = ctx.state.get("module", "")
    audience = ctx.state.get("audience", "tous")
    scenario = ctx.state.get("scenario", "")
    plan = ctx.state.get("plan", "")

    try:
        from app.agents.kb_llm_client import generate_kb_content_sync

        content = generate_kb_content_sync(
            system_prompt=KB_GENERATION_SYSTEM_PROMPT,
            user_prompt=get_kb_generation_prompt(
                title=title,
                module=module,
                audience=audience,
                scenario=scenario,
                plan=plan,
            ),
        )
    except Exception as e:
        logger.error("kb_content_generation_failed", error=str(e))
        return ctx.complete(
            message=(
                f"❌ Erreur lors de la génération du contenu : {str(e)[:200]}\n\n"
                "Vérifie que la clé OpenRouter est configurée dans le fichier .env "
                "(OPENROUTER_API_KEY)."
            )
        )

    ctx.add_tool_step("content generated")

    # Clean up the generated content — remove code fences if wrapped
    content = _clean_generated_content(content)

    # Build excerpt from first paragraph
    excerpt = _extract_excerpt(content)

    # Estimate read time
    read_time = _estimate_read_time(content)

    # Determine category
    category_slug = _infer_category_slug(module)

    # Create the article via repository
    slug = ctx.state.get("slug", _slugify_title(title))
    try:
        from app.domain.entities.kb_article import KBArticle, KBCategory

        # Try to find matching category
        category_id = None
        if category_slug:
            cat = ctx.db.query(KBCategory).filter(
                KBCategory.tenant_id == ctx.tenant_id,
                KBCategory.slug == category_slug,
            ).first()
            if cat:
                category_id = cat.id

        # Check if slug already exists
        existing = ctx.db.query(KBArticle).filter(
            KBArticle.tenant_id == ctx.tenant_id,
            KBArticle.slug == slug,
            KBArticle.is_deleted == False,
        ).first()
        if existing:
            # Append a suffix
            import uuid
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        article = KBArticle(
            title=title,
            slug=slug,
            excerpt=excerpt,
            content=content,
            category_id=category_id,
            tags=_infer_tags(module, audience),
            visibility="shared",
            author_name="Bob AI",
            author_role="Assistant IA",
            read_time_minutes=read_time,
            is_published=True,
            is_featured=False,
            tenant_id=ctx.tenant_id,
            created_by=ctx.user_email,
        )
        ctx.db.add(article)
        ctx.db.commit()
        ctx.db.refresh(article)

        # Update category article count
        if category_id:
            from app.infrastructure.persistence.kb_repository import KBRepository
            KBRepository(ctx.db).update_category_article_count(
                category_id, ctx.tenant_id
            )

        ctx.add_tool_step("article published")

        article_url = f"/knowledge-base/{slug}"

        ctx.emit_action("navigate", page=f"knowledge-base/{slug}")

        return ctx.complete(
            message=(
                f"✅ **Article publié avec succès !**\n\n"
                f"📝 **{title}**\n"
                f"📂 Module : {module}\n"
                f"👥 Public : {audience}\n"
                f"⏱️ Temps de lecture : {read_time} min\n\n"
                f"🔗 [Voir l'article]({article_url})\n\n"
                "N'hésite pas à me dire si tu souhaites des modifications !"
            )
        )

    except Exception as e:
        logger.error("kb_article_creation_failed", error=str(e))
        return ctx.complete(
            message=f"❌ Erreur lors de la création de l'article : {str(e)[:200]}"
        )


# ── Helper functions ─────────────────────────────────────────


def _infer_module(text: str) -> str:
    """Infer CRM module from user response."""
    text_lower = text.lower()
    module_map = {
        "contact": "Contacts",
        "organisation": "Organisations",
        "organization": "Organisations",
        "opportunité": "Opportunités",
        "opportunity": "Opportunités",
        "pipeline": "Pipeline",
        "catalogue": "Catalogue produits",
        "catalog": "Catalogue produits",
        "produit": "Catalogue produits",
        "activité": "Activités",
        "activity": "Activités",
        "paramètre": "Paramètres",
        "setting": "Paramètres",
        "dashboard": "Tableau de bord",
        "tableau de bord": "Tableau de bord",
        "bob": "Bob AI",
        "ia": "Bob AI",
        "ai": "Bob AI",
        "devis": "Devis",
        "quote": "Devis",
        "intégration": "Intégrations",
        "integration": "Intégrations",
    }
    for keyword, module in module_map.items():
        if keyword in text_lower:
            return module
    return "Général"


def _infer_audience(text: str) -> str:
    """Infer target audience from user response."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["admin", "administrateur", "super"]):
        return "Administrateurs"
    if any(w in text_lower for w in ["manager", "gestionnaire", "directeur"]):
        return "Gestionnaires"
    if any(w in text_lower for w in ["utilisateur", "user", "standard", "tous", "everyone"]):
        return "Tous les utilisateurs"
    return "Tous les utilisateurs"


def _generate_title(topic: str, module: str) -> str:
    """Generate a clean article title from topic and module."""
    # Clean up the topic
    topic_clean = topic.strip().rstrip(".")

    # Common prefix patterns
    prefixes = [
        "comment ", "how to ", "créer ", "crée ", "create ",
        "ajouter ", "add ", "configurer ", "configure ",
        "article sur ", "procédure pour ", "documentation pour ",
        "article de kb sur ", "article kb sur ",
        "base de connaissances sur ",
    ]

    title = topic_clean
    for prefix in prefixes:
        if title.lower().startswith(prefix):
            title = title[len(prefix):]
            break

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    # Ensure it starts with "Comment" for procedure-style articles
    if not any(title.lower().startswith(w) for w in ["comment", "guide", "introduction"]):
        title = f"Comment {title[0].lower()}{title[1:]}" if title else topic_clean

    return title


def _generate_plan(topic: str, module: str, details: str) -> str:
    """Generate a simple article plan based on the topic."""
    # Default plan structure — will be refined by LLM during generation
    steps = [
        "Accéder au module concerné",
        "Localiser la fonctionnalité",
        "Remplir les informations requises",
        "Valider et enregistrer",
        "Vérifier le résultat",
    ]

    # Customize based on common patterns
    topic_lower = topic.lower()
    if "créer" in topic_lower or "create" in topic_lower or "ajouter" in topic_lower:
        steps = [
            f"Accéder au module {module}",
            "Cliquer sur le bouton de création",
            "Remplir les champs obligatoires",
            "Ajouter les informations complémentaires",
            "Enregistrer et vérifier",
        ]
    elif "configurer" in topic_lower or "configure" in topic_lower:
        steps = [
            "Accéder aux paramètres",
            "Localiser la section de configuration",
            "Modifier les paramètres souhaités",
            "Enregistrer les modifications",
            "Tester la configuration",
        ]
    elif "chercher" in topic_lower or "search" in topic_lower or "trouver" in topic_lower:
        steps = [
            f"Accéder au module {module}",
            "Utiliser la barre de recherche",
            "Appliquer les filtres",
            "Consulter les résultats",
            "Ouvrir le résultat souhaité",
        ]

    return "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))


def _clean_generated_content(content: str) -> str:
    """Remove code fences and other artifacts from LLM output."""
    # Remove wrapping ```markdown ... ```
    content = re.sub(r"^```(?:markdown|md)?\s*\n", "", content)
    content = re.sub(r"\n```\s*$", "", content)
    # Remove thinking tags
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
    return content.strip()


def _extract_excerpt(content: str) -> str:
    """Extract a short excerpt from the article content."""
    # Find the first paragraph after "## Aperçu"
    match = re.search(r"## Aperçu\s*\n+(.+?)(?:\n\n|\n##)", content, re.DOTALL)
    if match:
        excerpt = match.group(1).strip()
        # Limit to ~200 chars
        if len(excerpt) > 200:
            excerpt = excerpt[:197] + "..."
        return excerpt

    # Fallback — first non-heading line
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("!"):
            return line[:200]
    return ""


def _infer_category_slug(module: str) -> str:
    """Map module name to KB category slug."""
    category_map = {
        "Contacts": "sales-crm",
        "Organisations": "sales-crm",
        "Opportunités": "sales-crm",
        "Pipeline": "sales-crm",
        "Catalogue produits": "sales-crm",
        "Activités": "sales-crm",
        "Tableau de bord": "getting-started",
        "Paramètres": "admin",
        "Bob AI": "ai-features",
        "Devis": "sales-crm",
        "Intégrations": "api",
        "Général": "getting-started",
    }
    return category_map.get(module, "getting-started")


def _infer_tags(module: str, audience: str) -> list[str]:
    """Generate relevant tags for the article."""
    tags = []

    module_tags = {
        "Contacts": ["contacts"],
        "Organisations": ["organisations"],
        "Opportunités": ["opportunités", "ventes"],
        "Pipeline": ["pipeline", "ventes"],
        "Catalogue produits": ["catalogue", "produits"],
        "Activités": ["activités"],
        "Tableau de bord": ["dashboard"],
        "Paramètres": ["configuration", "admin"],
        "Bob AI": ["bob", "ia"],
        "Devis": ["devis"],
        "Intégrations": ["api", "intégrations"],
    }
    tags.extend(module_tags.get(module, []))
    tags.append("procédure")

    if "admin" in audience.lower():
        tags.append("admin")

    return tags[:5]  # Max 5 tags
