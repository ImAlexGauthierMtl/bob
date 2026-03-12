"""
Seed 5 test organizations into the BCC with full profile data.
Vision, mission, culture, competition go into bcc_profile_entries.
A Sales Rep role is created under a Sales department per org.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import uuid
from app.infrastructure.database import SessionLocal
from app.domain.entities.bcc_entities import (
    BccOrganization, BccOrgProfile, BccDepartment, BccProfileEntry
)
import structlog

logger = structlog.get_logger(__name__)


ORGS = [
    {
        "name": "Videotron Solutions B2B",
        "description": "Division B2B de Videotron, offrant des solutions télécoms pour les entreprises.",
        "color": "#7B2D8B",
        "profile": {
            "country": "Canada",
            "state_province": "Quebec",
            "city": "Montreal",
            "operations_domains": ["Telecom", "Internet B2B", "Cloud Hosting"],
        },
        "knowledge": [
            {"section": "vision", "content": "Être le partenaire technologique #1 des PME québécoises d'ici 2028."},
            {"section": "mission", "content": "Connecter les entreprises avec des solutions fiables, rapides et abordables pour accélérer leur transformation numérique."},
            {"section": "culture", "content": "Esprit collaboratif, proximité client, innovation continue. On valorise la transparence et l'ownership individuel."},
            {"section": "competition", "content": "Bell Affaires, Rogers Entreprises, Telus Business. Avantage concurrentiel : ancrage québécois et support local."},
        ],
        "sales_role": {
            "title": "Représentant B2B — PME",
            "description": "Développe et maintient un portefeuille de PME au Québec. Gère le cycle complet de vente, de la prospection au renouvellement.",
            "sop": "1. Qualifier le lead (BANT). 2. Démo personnalisée. 3. Soumission avec 3 options. 4. Suivi à J+3, J+7. 5. Onboarding coordonné avec l'équipe CS.",
        }
    },
    {
        "name": "Madysta Hospitality Group",
        "description": "Groupe hôtelier québécois avec 14 propriétés, spécialisé dans l'expérience client premium.",
        "color": "#C8932A",
        "profile": {
            "country": "Canada",
            "state_province": "Quebec",
            "city": "Quebec City",
            "operations_domains": ["Hospitality", "Events", "F&B", "Spa"],
        },
        "knowledge": [
            {"section": "vision", "content": "Redéfinir l'hospitalité québécoise en créant des expériences mémorables ancrées dans la culture locale."},
            {"section": "mission", "content": "Offrir à chaque client une expérience personnalisée qui dépasse ses attentes, portée par des équipes engagées et fières de leur région."},
            {"section": "culture", "content": "Passion du service, authenticité, excellence opérationnelle. Chaque employé est un ambassadeur de la marque."},
            {"section": "competition", "content": "Fairmont, Accor, hôtels boutique indépendants. Force : portefeuille unique de propriétés québécoises + fidélité locale."},
        ],
        "sales_role": {
            "title": "Conseiller Ventes — Groupes & Événements",
            "description": "Développe les relations avec les planificateurs d'événements, entreprises et agences de voyage pour maximiser le RevPAR des propriétés.",
            "sop": "1. Répondre aux RFP en <4h. 2. Site visit personnalisée. 3. Proposition customisée avec options F&B. 4. Négociation et contrat. 5. Briefing opérationnel pré-événement.",
        }
    },
    {
        "name": "NovaPharma Québec",
        "description": "Distributeur pharmaceutique régional desservant cliniques, pharmacies et hôpitaux au Québec.",
        "color": "#1A5276",
        "profile": {
            "country": "Canada",
            "state_province": "Quebec",
            "city": "Laval",
            "operations_domains": ["Pharma Distribution", "Medical Devices", "Healthcare IT"],
        },
        "knowledge": [
            {"section": "vision", "content": "Améliorer l'accès aux médicaments et dispositifs médicaux pour chaque Québécois, où qu'il soit."},
            {"section": "mission", "content": "Assurer la distribution fiable et conforme de produits pharmaceutiques en bâtissant des partenariats durables avec les professionnels de la santé."},
            {"section": "culture", "content": "Rigueur, conformité réglementaire, éthique absolue. La sécurité patient prime sur tout."},
            {"section": "competition", "content": "McKesson, Propharex, AmerisourceBergen Canada. Avantage : réactivité régionale et relations directes avec les cliniciens."},
        ],
        "sales_role": {
            "title": "Délégué Médical — Comptes Stratégiques",
            "description": "Développe les relations avec les responsables d'achats des CISSS, hôpitaux et chaînes de pharmacies. Conduit les appels d'offres publics.",
            "sop": "1. Cartographier les influenceurs (prescripteur, acheteur, DG). 2. Visite terrain bimensuelle. 3. Réponse aux appels d'offres (AO). 4. Formation produit auprès des équipes. 5. Revue de compte trimestrielle.",
        }
    },
    {
        "name": "Croo Labs",
        "description": "Studio SaaS spécialisé dans le développement d'outils IA pour les équipes de vente et de recrutement.",
        "color": "#E74C3C",
        "profile": {
            "country": "Canada",
            "state_province": "Quebec",
            "city": "Montreal",
            "operations_domains": ["SaaS", "AI Tools", "Sales Enablement", "HR Tech"],
        },
        "knowledge": [
            {"section": "vision", "content": "Construire l'OS des équipes performantes — où chaque rep a un co-pilote IA dédié."},
            {"section": "mission", "content": "Réduire la friction administrative des sales reps pour qu'ils consacrent 80% de leur temps à vendre, pas à entrer des données."},
            {"section": "culture", "content": "Move fast, ship often. Culture de la mesure : tout se décide par les données. Ownership total sur ses résultats."},
            {"section": "competition", "content": "Salesforce, HubSpot, monday.com. Avantage : IA native, onboarding <1h, pricing SMB-friendly."},
        ],
        "sales_role": {
            "title": "Account Executive — SaaS B2B",
            "description": "Gère le cycle de vente complet (ACV 8K-80K$) pour les équipes de vente de 10-100 reps. Spécialiste du demo-driven sales.",
            "sop": "1. Discovery call 30min (pain + budget + timeline). 2. Demo personnalisée J+3. 3. POC 14 jours avec success criteria. 4. Proposition ROI chiffrée. 5. Close + handoff CS.",
        }
    },
    {
        "name": "ConstructionPlus Montréal",
        "description": "Entrepreneur général résidentiel et commercial, 200+ employés, actif sur l'île de Montréal et Rive-Sud.",
        "color": "#F39C12",
        "profile": {
            "country": "Canada",
            "state_province": "Quebec",
            "city": "Montreal",
            "operations_domains": ["Construction Résidentielle", "Construction Commerciale", "Rénovation", "Gérance de projet"],
        },
        "knowledge": [
            {"section": "vision", "content": "Bâtir le Montréal de demain avec des projets durables, livrés à temps et dans les budgets."},
            {"section": "mission", "content": "Offrir aux promoteurs et municipalités une exécution impeccable grâce à une équipe de métiers qualifiés et une gestion de projet rigoureuse."},
            {"section": "culture", "content": "Terrain avant tout. Respect du métier, des délais et des gens. On dit ce qu'on fait, on fait ce qu'on dit."},
            {"section": "competition", "content": "Pomerleau, Elema, Broccolini. Force : réactivité pour les projets <5M$ et réseau local de sous-traitants établis."},
        ],
        "sales_role": {
            "title": "Chargé de développement — Projets Commerciaux",
            "description": "Développe de nouveaux mandats avec des promoteurs, architectes et gestionnaires d'immeubles. Gère les soumissions et les relations clients de projet.",
            "sop": "1. Qualifier le projet (budget, échéancier, portée). 2. Visite terrain avec estimateur. 3. Dépôt soumission à J+5. 4. Présentation et négociation. 5. Kick-off projet et suivi mensuel client.",
        }
    }
]


def run_seed():
    db = SessionLocal()
    try:
        # Get tenant_id from existing org
        existing = db.query(BccOrganization).first()
        if not existing:
            logger.error("No existing BCC org found — run main seed first")
            return
        tenant_id = existing.tenant_id

        created = 0
        for org_data in ORGS:
            # Skip if already exists
            exists = db.query(BccOrganization).filter(
                BccOrganization.name == org_data["name"],
                BccOrganization.tenant_id == tenant_id
            ).first()
            if exists:
                logger.info("org_already_exists", name=org_data["name"])
                org = exists
            else:
                # Create organization
                org = BccOrganization(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    name=org_data["name"],
                    description=org_data["description"],
                    color=org_data.get("color"),
                )
                db.add(org)
                db.flush()

                # Create org profile
                profile_data = org_data["profile"]
                org_profile = BccOrgProfile(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    organization_id=org.id,
                    country=profile_data.get("country"),
                    state_province=profile_data.get("state_province"),
                    city=profile_data.get("city"),
                    operations_domains=profile_data.get("operations_domains", []),
                )
                db.add(org_profile)

                # Create knowledge entries (vision, mission, culture, competition)
                for k in org_data["knowledge"]:
                    entry = BccProfileEntry(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        entity_type="organization",
                        entity_id=org.id,
                        section=k["section"],
                        perspective="general",
                        content=k["content"],
                        contribution_method="import",
                        is_active=True,
                        version=1,
                    )
                    db.add(entry)

                created += 1
                logger.info("org_created", name=org_data["name"])

            # Create Sales dept + Sales Rep role if not already there
            sales_dept = db.query(BccDepartment).filter(
                BccDepartment.organization_id == org.id,
                BccDepartment.name == "Ventes",
            ).first()
            if not sales_dept:
                sales_dept = BccDepartment(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    organization_id=org.id,
                    name="Ventes",
                    description="Équipe commerciale et développement des affaires.",
                )
                db.add(sales_dept)
                db.flush()

                # Add sales rep role knowledge entry on the dept
                role_data = org_data["sales_role"]
                role_entry = BccProfileEntry(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    entity_type="department",
                    entity_id=sales_dept.id,
                    section="sales_rep_role",
                    perspective="general",
                    content=f"**{role_data['title']}**\n\n{role_data['description']}\n\n**SOP:**\n{role_data['sop']}",
                    contribution_method="import",
                    is_active=True,
                    version=1,
                )
                db.add(role_entry)
                logger.info("sales_dept_created", org=org_data["name"], role=role_data["title"])

        db.commit()
        logger.info("seed_complete", orgs_created=created)
        print(f"\n✅ Seeded: {created} new orgs (skipped existing). Total orgs in tenant: {db.query(BccOrganization).filter_by(tenant_id=tenant_id).count()}")

    except Exception as e:
        db.rollback()
        logger.error("seed_failed", error=str(e))
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
