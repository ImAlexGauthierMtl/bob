"""Enrich contact via Bright Data LinkedIn scraping.

Triggered explicitly by user clicking "Bob's Rolodex" on a contact.
1. Calls Bright Data to scrape LinkedIn profile
2. Merges data into contact_profile JSON
3. Updates flat fields: headline, profile_picture_url
4. Creates an activity TASK summarizing findings
"""

import structlog
from sqlalchemy.orm import Session

from app.infrastructure.external.bright_data_service import BrightDataService
from app.infrastructure.persistence.contact_repository import ContactRepository
from app.infrastructure.persistence.activity_repository import ActivityRepository

logger = structlog.get_logger(__name__)


class EnrichContactLinkedInUseCase:
    """Enrich a contact with LinkedIn data via Bright Data."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.contact_repo = ContactRepository(db)
        self.activity_repo = ActivityRepository(db)
        self.bright_data = BrightDataService()

    async def execute(self, contact_id: str, tenant_id: str, user_email: str) -> dict:
        """Run LinkedIn enrichment for a contact."""
        contact = self.contact_repo.get_by_id(contact_id, tenant_id)
        if not contact:
            return {"status": "error", "error": "Contact not found"}

        linkedin_url = contact.linkedin_url
        # Fallback: Hunter.io stores LinkedIn in contact_profile
        if not linkedin_url and contact.contact_profile:
            linkedin_url = contact.contact_profile.get("linkedin")
        if not linkedin_url:
            return {"status": "error", "error": "No LinkedIn URL on this contact"}

        logger.info(
            "contact_linkedin_enrichment_start",
            contact_id=contact_id,
            name=f"{contact.first_name} {contact.last_name}",
            linkedin_url=linkedin_url,
        )

        # 1. Call Bright Data
        profile_data = await self.bright_data.scrape_linkedin_profile(linkedin_url)

        if not profile_data:
            return {"status": "error", "error": "Bright Data returned no data"}

        # 2. Merge into contact_profile
        existing_profile = contact.contact_profile or {}
        existing_profile["bright_data"] = profile_data
        existing_profile["linkedin_enriched"] = True

        # 3. Update flat fields
        update_data = {"contact_profile": existing_profile}

        if profile_data.get("headline"):
            update_data["headline"] = profile_data["headline"]
        if profile_data.get("profile_picture_url"):
            update_data["profile_picture_url"] = profile_data["profile_picture_url"]
        if profile_data.get("followers"):
            update_data["linkedin_followers"] = profile_data["followers"]

        self.contact_repo.update(contact_id, tenant_id, update_data)
        self.db.commit()

        # 4. Create enrichment activity
        self._create_enrichment_activity(
            contact_id=contact_id,
            contact_name=f"{contact.first_name} {contact.last_name}",
            tenant_id=tenant_id,
            user_email=user_email,
            profile_data=profile_data,
        )

        logger.info(
            "contact_linkedin_enrichment_done",
            contact_id=contact_id,
            name=f"{contact.first_name} {contact.last_name}",
            fields_enriched=list(profile_data.keys()),
        )

        return {
            "status": "done",
            "contact_id": contact_id,
            "fields_enriched": list(profile_data.keys()),
        }

    def _create_enrichment_activity(
        self,
        *,
        contact_id: str,
        contact_name: str,
        tenant_id: str,
        user_email: str,
        profile_data: dict,
    ) -> None:
        """Create a TASK activity summarizing LinkedIn enrichment."""
        parts = [f"🤖 Bob's Rolodex a enrichi **{contact_name}** via LinkedIn (Bright Data).\n"]

        if profile_data.get("headline"):
            parts.append(f"• Headline : {profile_data['headline']}")
        if profile_data.get("about"):
            about_preview = profile_data["about"][:200]
            parts.append(f"• À propos : {about_preview}...")
        if profile_data.get("work_experience"):
            parts.append(f"• {len(profile_data['work_experience'])} expériences professionnelles")
        if profile_data.get("education"):
            parts.append(f"• {len(profile_data['education'])} formations")
        if profile_data.get("skills"):
            skills_preview = ", ".join(profile_data["skills"][:5])
            parts.append(f"• Compétences : {skills_preview}")
        if profile_data.get("connections"):
            parts.append(f"• {profile_data['connections']} connexions LinkedIn")
        if profile_data.get("certifications"):
            parts.append(f"• {len(profile_data['certifications'])} certifications")

        description = "\n".join(parts)

        try:
            self.activity_repo.create(
                {
                    "subject": f"Bob's Rolodex — {contact_name}",
                    "description": description,
                    "activity_type": "TASK",
                    "status": "COMPLETED",
                    "priority": "LOW",
                    "assigned_to": "Bob (AI Agent)",
                    "contact_ids": [contact_id],
                },
                tenant_id=tenant_id,
            )
            self.db.commit()
            logger.info(
                "contact_enrichment_activity_created",
                contact_id=contact_id,
                contact_name=contact_name,
            )
        except Exception as e:
            logger.error("contact_enrichment_activity_error", error=str(e))
