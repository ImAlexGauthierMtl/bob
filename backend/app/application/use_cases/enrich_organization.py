"""Enrich organization use case — runs in background.

Maps already provides: name, address, phone, website, industry.
This use case runs the full pipeline:
1. Hunter.io contacts + company enrichment
2. Website scraping
3. Groq LLM extraction (flat fields + deep profile)
4. Groq Compound deep intelligence (news, clients, competitors)

Also auto-creates Contact entities from Hunter.io data.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session
import structlog

from app.agents.enrichment_graph import run_enrichment
from app.domain.entities.contact import Contact
from app.infrastructure.persistence.organization_repository import OrganizationRepository
from app.infrastructure.persistence.contact_repository import ContactRepository
from app.infrastructure.persistence.activity_repository import ActivityRepository

logger = structlog.get_logger(__name__)


class EnrichOrganizationUseCase:
    """Run the AI enrichment pipeline and persist results."""

    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.contact_repo = ContactRepository(db)
        self.activity_repo = ActivityRepository(db)

    async def execute(self, org_id: str, tenant_id: str, user_email: str) -> dict:
        """Enrich an organization with AI-gathered data.

        Runs the full pipeline and persists:
        - Flat fields: description, employee_count, revenue, linkedin, etc.
        - Deep profile: services, contacts, social media, key people.
        - Intelligence sections: news, clients, competitors, etc.
        - Auto-created contacts from Hunter.io data.
        """
        org = self.org_repo.get_by_id(org_id, tenant_id)
        if not org:
            logger.error("enrichment_org_not_found", org_id=org_id)
            return {"status": "error", "error": "Organization not found", "fields_updated": 0, "fields": {}}

        # Use the website from Maps data for scraping
        website_url = org.website

        result = await run_enrichment(
            organization_id=org_id,
            organization_name=org.name,
            tenant_id=tenant_id,
            user_email=user_email,
            website_url=website_url,
        )

        pipeline_status = result.get("status", "error")

        if pipeline_status == "error" and not result.get("extracted") and not result.get("organization_profile"):
            return {
                "status": "error",
                "error": result.get("error", "Both flat and deep extraction failed"),
                "fields_updated": 0,
                "fields": {},
            }

        # ── Apply flat extracted fields — only fill empty fields ──
        extracted = result.get("extracted", {})
        updated_count = 0

        allowed_fields = [
            "industry", "website", "phone", "email",
            "address_street", "address_city", "address_state",
            "address_country", "address_postal_code",
            "employee_count", "annual_revenue", "description",
            "linkedin_url", "org_type",
        ]

        for field in allowed_fields:
            if field in extracted and extracted[field]:
                current_value = getattr(org, field, None)
                if not current_value:
                    setattr(org, field, extracted[field])
                    updated_count += 1

        # ── Apply Hunter.io company data to flat fields (fill gaps) ──
        hunter_company = result.get("hunter_company", {})
        if hunter_company:
            hunter_field_map = {
                "industry": "industry",
                "phone": "phone",
                "description": "description",
                "founded_year": "founded_year",
            }
            for hunter_key, org_field in hunter_field_map.items():
                val = hunter_company.get(hunter_key)
                if val and hasattr(org, org_field):
                    current = getattr(org, org_field, None)
                    if not current:
                        setattr(org, org_field, val)
                        updated_count += 1

            # LinkedIn from Hunter social
            social = hunter_company.get("social", {})
            if social.get("linkedin") and not getattr(org, "linkedin_url", None):
                org.linkedin_url = social["linkedin"]
                updated_count += 1

        # ── Save deep profile (merge Hunter + intelligence sections) ──
        organization_profile = result.get("organization_profile", {})
        hunter_contacts = result.get("hunter_contacts", [])
        intelligence_sections = result.get("intelligence_sections", [])

        if hunter_contacts:
            organization_profile["hunter_contacts"] = hunter_contacts
            logger.info("hunter_contacts_saved", org_id=org_id, count=len(hunter_contacts))

        if hunter_company:
            organization_profile["hunter_company"] = hunter_company

        if intelligence_sections:
            organization_profile["intelligence_sections"] = intelligence_sections
            logger.info(
                "intelligence_sections_saved",
                org_id=org_id,
                sections=[s.get("id") for s in intelligence_sections],
            )

        if organization_profile:
            org.organization_profile = organization_profile
            logger.info("deep_profile_saved", org_id=org_id, categories=list(organization_profile.keys()))

        # ── Auto-create contacts from Hunter.io data ──
        contacts_created = 0
        if hunter_contacts:
            contacts_created = self._create_hunter_contacts(
                hunter_contacts=hunter_contacts,
                org_id=org_id,
                tenant_id=tenant_id,
                user_email=user_email,
            )

        # Only mark fully enriched when both extractions succeeded
        if pipeline_status == "done":
            org.ai_enriched = "Y"
        elif pipeline_status == "partial":
            org.ai_enriched = "P"
        org.updated_by = f"ai-agent ({user_email})"

        self.org_repo.update(org)

        logger.info(
            "enrichment_persisted",
            org_id=org_id,
            org_name=org.name,
            pipeline_status=pipeline_status,
            fields_updated=updated_count,
            has_profile=bool(organization_profile),
            hunter_contacts=len(hunter_contacts),
            contacts_created=contacts_created,
            intelligence_sections=len(intelligence_sections),
        )

        # ── Create enrichment activity linked to the org ──
        self._create_enrichment_activity(
            org_id=org_id,
            org_name=org.name,
            tenant_id=tenant_id,
            user_email=user_email,
            pipeline_status=pipeline_status,
            fields_updated=updated_count,
            contacts_created=contacts_created,
            hunter_contacts_count=len(hunter_contacts),
            intelligence_sections=intelligence_sections,
            organization_profile=organization_profile,
        )

        return {
            "status": pipeline_status,
            "fields_updated": updated_count,
            "fields": extracted,
            "organization_profile": organization_profile,
            "hunter_contacts": hunter_contacts,
            "contacts_created": contacts_created,
            "intelligence_sections": len(intelligence_sections),
            "error": None if pipeline_status == "done" else f"Enrichment completed with status: {pipeline_status}",
        }

    def _create_hunter_contacts(
        self,
        hunter_contacts: list,
        org_id: str,
        tenant_id: str,
        user_email: str,
    ) -> int:
        """Auto-create Contact entities from Hunter.io data.

        Skips contacts that already exist (matched by email).
        Stores Hunter metadata in contact_profile JSON.
        """
        created = 0
        for hc in hunter_contacts:
            email = hc.get("email")
            if not email:
                continue

            # Skip generic email-only contacts (no first name = no identity)
            first_name = hc.get("first_name")
            last_name = hc.get("last_name")
            if not first_name:
                logger.info("hunter_contact_skip_no_name", email=email)
                continue

            # Check if contact already exists
            existing = self.db.query(Contact).filter(
                Contact.email == email,
                Contact.tenant_id == tenant_id,
                Contact.is_deleted == False,  # noqa: E712
            ).first()

            if existing:
                # Update contact_profile with Hunter data if not set
                if not existing.contact_profile:
                    existing.contact_profile = self._build_contact_profile(hc)
                    existing.version += 1
                    self.db.commit()
                continue

            # Build new contact
            contact = Contact(
                first_name=first_name,
                last_name=last_name or "",
                email=email,
                phone=hc.get("phone"),
                job_title=hc.get("position"),
                department=hc.get("department"),
                seniority=hc.get("seniority"),
                linkedin_url=hc.get("linkedin"),
                organization_id=org_id,
                tenant_id=tenant_id,
                created_by=f"ai-agent ({user_email})",
                updated_by=f"ai-agent ({user_email})",
                contact_profile=self._build_contact_profile(hc),
            )
            self.db.add(contact)
            created += 1

        if created > 0:
            self.db.commit()
            logger.info("hunter_contacts_created", org_id=org_id, count=created)

        return created

    @staticmethod
    def _build_contact_profile(hc: dict) -> dict:
        """Build contact_profile JSON from Hunter.io data."""
        return {
            "source": "hunter.io",
            "confidence": hc.get("confidence"),
            "verification_status": hc.get("verification_status"),
            "department": hc.get("department"),
            "position_raw": hc.get("position_raw"),
            "linkedin": hc.get("linkedin"),
            "phone": hc.get("phone"),
            "seniority": hc.get("seniority"),
        }

    def _create_enrichment_activity(
        self,
        *,
        org_id: str,
        org_name: str,
        tenant_id: str,
        user_email: str,
        pipeline_status: str,
        fields_updated: int,
        contacts_created: int,
        hunter_contacts_count: int,
        intelligence_sections: list,
        organization_profile: dict,
    ) -> None:
        """Create a TASK activity summarizing what Bob found during enrichment."""
        try:
            # ── Build summary description ──
            lines = [f"🤖 Bob a enrichi automatiquement **{org_name}**.\n"]

            if fields_updated:
                lines.append(f"• {fields_updated} champs mis à jour (industrie, description, téléphone, etc.)")

            if hunter_contacts_count:
                lines.append(f"• {hunter_contacts_count} contacts trouvés via Hunter.io")
                if contacts_created:
                    lines.append(f"  → {contacts_created} nouveaux contacts créés")

            if intelligence_sections:
                section_titles = [s.get("title", s.get("id", "?")) for s in intelligence_sections]
                lines.append(f"• {len(intelligence_sections)} sections d'intelligence générées :")
                for title in section_titles:
                    lines.append(f"  — {title}")

            # Profile categories summary
            profile_keys = [k for k in organization_profile.keys()
                           if k not in ("hunter_contacts", "hunter_company", "intelligence_sections")]
            if profile_keys:
                lines.append(f"• Profil enrichi : {', '.join(profile_keys)}")

            lines.append(f"\nStatut : {pipeline_status.upper()}")

            description = "\n".join(lines)

            activity_data = {
                "subject": f"Bob Enrichment — {org_name}",
                "description": description,
                "activity_type": "TASK",
                "priority": "LOW",
                "status": "COMPLETED",
                "assigned_to": "Bob (AI Agent)",
                "organization_ids": [org_id],
            }

            activity = self.activity_repo.create(activity_data, tenant_id)
            activity.created_by = f"bob-enrichment ({user_email})"
            activity.completed_at = datetime.now(timezone.utc)
            self.db.commit()

            logger.info(
                "enrichment_activity_created",
                org_id=org_id,
                activity_id=activity.id,
                org_name=org_name,
            )
        except Exception as e:
            logger.warning("enrichment_activity_error", org_id=org_id, error=str(e))
