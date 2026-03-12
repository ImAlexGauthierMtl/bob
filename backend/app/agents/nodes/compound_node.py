"""Compound node — Groq Compound deep intelligence enrichment.

Uses groq/compound model to perform autonomous web searches and
produce dynamic intelligence sections (news, clients, competitors, etc.).
"""

from __future__ import annotations

import json
import re
from typing import Any

import structlog

from app.config import settings
from app.agents.state import EnrichmentState
from app.infrastructure.database import SessionLocal
from app.middleware.usage_tracker import UsageTracker
from app.domain.entities.usage_transaction import TriggerSource

logger = structlog.get_logger(__name__)

# ── System prompt — instructs Compound to return structured sections ──
COMPOUND_SYSTEM_PROMPT = """Tu es un spécialiste en intelligence d'affaires (BI). Tu reçois des données sur une entreprise et ses contacts, déjà collectées par d'autres outils. Ta mission: APPROFONDIR en cherchant le web pour trouver ce qui manque.

Tu dois retourner un JSON avec une clé "sections" contenant un tableau de sections. Chaque section a:
- "id": identifiant unique snake_case
- "title": titre en français
- "icon": classe FontAwesome (ex: "fa-solid fa-newspaper")
- "type": un de "tags", "key_value", "table", "list"
- Selon le type:
  - tags: "items" = ["tag1", "tag2"]
  - key_value: "entries" = [{"label": "...", "value": "..."}]
  - table: "columns" = ["Col1", "Col2"], "rows" = [["val1", "val2"]]
  - list: "items" = ["item1", "item2"]

Sections à produire (si données trouvées):
1. "recent_news" (table) — Actualités, articles de presse, publications récentes
2. "known_clients" (tags) — Clients identifiés, témoignages, études de cas
3. "competitors" (tags) — Concurrents directs dans la région/secteur
4. "online_presence" (key_value) — Annuaires, avis Google/Facebook, présence web
5. "partnerships" (tags) — Partenariats stratégiques identifiés
6. "recommendations" (list) — Recommandations pour la prospection
7. "tech_stack" (tags) — Technologies utilisées (si pertinent)
8. "certifications" (tags) — Certifications, accréditations professionnelles

N'inclus QUE les sections où tu trouves des données réelles.
Retourne UNIQUEMENT le JSON, rien d'autre.
"""


def _build_context(state: EnrichmentState) -> str:
    """Build context string from all collected data."""
    parts: list[str] = []

    parts.append(f"## Entreprise: {state['organization_name']}")

    # Hunter company data
    hunter_company = state.get("hunter_company", {})
    if hunter_company:
        parts.append(f"\n### Données Hunter.io (Company)")
        for key, val in hunter_company.items():
            if val and key != "social":
                parts.append(f"- {key}: {val}")
        social = hunter_company.get("social", {})
        if social:
            for platform, url in social.items():
                if url:
                    parts.append(f"- {platform}: {url}")

    # Hunter contacts
    hunter_contacts = state.get("hunter_contacts", [])
    if hunter_contacts:
        parts.append(f"\n### Contacts vérifiés ({len(hunter_contacts)})")
        for c in hunter_contacts:
            line = f"- {c.get('first_name', '')} {c.get('last_name', '')} — {c.get('position', 'N/A')}"
            if c.get("email"):
                line += f" — {c['email']}"
            if c.get("department"):
                line += f" — Dept: {c['department']}"
            parts.append(line)

    # Scraped data summary (truncated)
    scraped = state.get("scraped_data", [])
    if scraped:
        parts.append(f"\n### Contenu web scrapé ({len(scraped)} pages)")
        for page in scraped[:3]:
            content = page.get("content", "")[:800]
            parts.append(f"URL: {page.get('url', 'N/A')}")
            parts.append(content)

    # Extracted profile
    extracted = state.get("extracted", {})
    if extracted:
        parts.append("\n### Champs extraits")
        for k, v in extracted.items():
            if v:
                parts.append(f"- {k}: {v}")

    # Organization profile from extraction
    org_profile = state.get("organization_profile", {})
    if org_profile:
        parts.append("\n### Profil structuré")
        for section, data in org_profile.items():
            if data and section not in ("hunter_contacts", "hunter_company"):
                parts.append(f"- {section}: {json.dumps(data, ensure_ascii=False)[:300]}")

    return "\n".join(parts)


def _parse_sections(content: str) -> list[dict[str, Any]]:
    """Parse intelligence sections from LLM response."""
    # Try to extract JSON from response
    try:
        # Direct JSON parse
        data = json.loads(content)
        return data.get("sections", [])
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in markdown
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            return data.get("sections", [])
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object
    brace_match = re.search(r'\{[^{}]*"sections"[^{}]*\[.*\]\s*\}', content, re.DOTALL)
    if brace_match:
        try:
            data = json.loads(brace_match.group(0))
            return data.get("sections", [])
        except json.JSONDecodeError:
            pass

    logger.warning("compound_parse_failed", content_preview=content[:200])
    return []


def _validate_section(section: dict) -> bool:
    """Validate a single intelligence section has required fields."""
    required = {"id", "title", "type"}
    if not all(k in section for k in required):
        return False
    valid_types = {"tags", "key_value", "table", "list"}
    if section["type"] not in valid_types:
        return False
    # Must have content
    if section["type"] == "tags" and not section.get("items"):
        return False
    if section["type"] == "key_value" and not section.get("entries"):
        return False
    if section["type"] == "table" and (not section.get("columns") or not section.get("rows")):
        return False
    if section["type"] == "list" and not section.get("items"):
        return False
    return True


def _track_usage(state: EnrichmentState, input_tokens: int = 0, output_tokens: int = 0) -> None:
    """Track Groq Compound usage."""
    try:
        db = SessionLocal()
        tracker = UsageTracker(db)
        tracker.track_llm(
            tenant_id=state["tenant_id"],
            user_id=state.get("user_email", "system"),
            user_email=state.get("user_email", "system"),
            provider="groq",
            model="groq/compound",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            trigger_source=TriggerSource.ENRICHMENT,
            metadata={
                "organization": state["organization_name"],
                "service": "compound_search",
            },
        )
        db.commit()
        db.close()
    except Exception as e:
        logger.warning("compound_track_error", error=str(e))


async def compound_node(state: EnrichmentState) -> dict:
    """Groq Compound deep intelligence enrichment.

    Uses groq/compound to autonomously search the web and produce
    structured intelligence sections about the organization.

    Gracefully skips if:
    - GROQ_API_KEY is not configured
    - No meaningful data has been collected yet
    """
    name = state["organization_name"]

    # ── Check prerequisites ──
    if not settings.groq_api_key:
        logger.info("compound_skip_no_key", organization=name)
        return {"intelligence_sections": [], "status": "done"}

    # Need at least some data to enrich
    has_hunter = bool(state.get("hunter_contacts") or state.get("hunter_company"))
    has_scraped = bool(state.get("scraped_data"))
    has_extracted = bool(state.get("organization_profile"))

    if not (has_hunter or has_scraped or has_extracted):
        logger.info("compound_skip_no_data", organization=name)
        return {"intelligence_sections": [], "status": "done"}

    logger.info("compound_start", organization=name)

    try:
        from groq import Groq

        client = Groq(api_key=settings.groq_api_key)
        context = _build_context(state)

        response = client.chat.completions.create(
            model="groq/compound",
            messages=[
                {"role": "system", "content": COMPOUND_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Enrichis cette entreprise en profondeur:\n\n{context}",
                },
            ],
            temperature=0.2,
            max_tokens=4096,
        )

        content = response.choices[0].message.content or ""
        usage = response.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0
        sections = _parse_sections(content)

        # Validate and filter
        valid_sections = [s for s in sections if _validate_section(s)]

        _track_usage(state, input_tokens=tokens_in, output_tokens=tokens_out)

        logger.info(
            "compound_done",
            organization=name,
            sections_found=len(valid_sections),
            section_ids=[s["id"] for s in valid_sections],
        )

        return {
            "intelligence_sections": valid_sections,
            "status": "done",
        }

    except Exception as e:
        logger.error("compound_error", organization=name, error=str(e))
        return {"intelligence_sections": [], "status": "done"}
