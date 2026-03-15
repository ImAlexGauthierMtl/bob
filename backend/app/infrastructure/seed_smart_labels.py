"""Seed Smart Labels — CEO inbox categories for AI email classification.

Creates 15 enriched Smart Label categories optimized for LLM-based
email triage (Llama via Groq). Each label includes:
- description: explains the category to the AI
- keywords: trigger phrases/words for matching
- prompt_hint: explicit instruction to guide the LLM decision
"""

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.smart_label import SmartLabel

logger = structlog.get_logger(__name__)

# ── Category Definitions ─────────────────────────────────────────
# Each entry maps to a SmartLabel row. The AI uses description,
# keywords, and prompt_hint together to classify incoming emails.

CEO_INBOX_CATEGORIES = [
    {
        "name": "[ACTION]",
        "color": "#E53E3E",
        "description": (
            "Priorité Critique — Emails nécessitant une décision, une signature "
            "ou une réponse directe du CEO sous 24h. Cela inclut les questions "
            "directes du C-Level, les urgences opérationnelles majeures et les "
            "validations bloquantes."
        ),
        "keywords": [
            "Approbation nécessaire", "Urgent", "Validation", "Dès que possible",
            "ASAP", "Signature requise", "Décision", "Bloquant", "Critique",
            "Action requise", "Prioritaire", "Immédiat", "Deadline",
            "Besoin de votre approbation", "En attente de votre validation",
        ],
        "prompt_hint": (
            "Assign this label ONLY when the email explicitly requests a decision, "
            "a signature, or a direct response from the CEO within a short deadline. "
            "The sender should be a C-Level executive, a direct report, or someone "
            "with a blocking dependency. Generic FYI emails do NOT qualify."
        ),
    },
    {
        "name": "[CLIENTS]",
        "color": "#3182CE",
        "description": (
            "Relations VIP & Comptes Clés — Communications directes avec les "
            "clients stratégiques ou les comptes à haute valeur. Inclut les retours "
            "d'expérience, plaintes majeures de clients, demandes de rendez-vous "
            "de comptes existants, et escalades client."
        ),
        "keywords": [
            "Success Manager", "Satisfaction client", "Client VIP",
            "Compte clé", "Escalade", "Réclamation", "Renouvellement",
            "SLA", "Expérience client", "NPS", "Customer success",
            "Fidélisation", "Retour client", "Feedback client",
        ],
        "prompt_hint": (
            "Assign when the email comes from or directly concerns an existing "
            "client or key account. Look for client domain names, account manager "
            "references, support escalations, renewal discussions, or satisfaction "
            "feedback. Do NOT assign for new prospects (use [VENTES] instead)."
        ),
    },
    {
        "name": "[PROJETS]",
        "color": "#38A169",
        "description": (
            "Développement & Chantiers Internes — Suivi opérationnel des projets "
            "en cours, notamment le CRM, l'ERP et l'Assistant Virtuel IA. Inclut "
            "les updates sur les sprints, blocages techniques liés à Python/Angular, "
            "spécifications fonctionnelles et déploiements."
        ),
        "keywords": [
            "Sprint", "User Story", "MVP", "Backend", "Frontend",
            "Déploiement", "Jira", "Git", "Pull request", "Release",
            "Roadmap technique", "Architecture", "API", "Bug fix",
            "Code review", "Spécification", "Milestone",
        ],
        "prompt_hint": (
            "Assign when the email discusses internal project progress, development "
            "updates, sprint reviews, technical decisions, or deployment status. "
            "Typical senders are developers, product managers, or tech leads. "
            "Pure R&D / innovation research goes to [PRODUIT] instead."
        ),
    },
    {
        "name": "[PARTNERSHIPS]",
        "color": "#805AD5",
        "description": (
            "Alliances & Écosystème — Discussions avec des partenaires externes, "
            "technologiques ou commerciaux. Inclut co-marketing, intégrations API "
            "tierces, protocoles d'accord (MoU), et négociations de partenariat."
        ),
        "keywords": [
            "Synergie", "Collaboration", "Joint venture", "Intégration partenaire",
            "MoU", "Protocole d'accord", "Co-marketing", "Partenariat",
            "Alliance stratégique", "Reseller", "Affiliate", "Channel partner",
            "White label", "Co-développement", "Ecosystem",
        ],
        "prompt_hint": (
            "Assign when the email involves discussions with external partners — "
            "technology integrations, co-marketing proposals, MoU negotiations, "
            "reseller agreements, or joint ventures. The sender is typically from "
            "a partner company, not an internal team member or a client."
        ),
    },
    {
        "name": "[CONFERENCES]",
        "color": "#DD6B20",
        "description": (
            "Événements & Networking — Invitations à parler, logistique de salons "
            "professionnels ou événements de networking. Inclut invitations en tant "
            "que speaker, billets de conférences et logistique de stands."
        ),
        "keywords": [
            "Keynote", "Panel", "Sommet", "Webinar", "Invitation speaker",
            "Conférence", "Salon", "Summit", "Networking event", "Meetup",
            "Table ronde", "Workshop", "Hackathon", "Demo day",
            "Stand", "Exposition", "Forum",
        ],
        "prompt_hint": (
            "Assign when the email is an invitation to speak, attend, or sponsor "
            "a conference, summit, webinar, or networking event. Also assign for "
            "event logistics (stand setup, travel for events, speaker briefs). "
            "Generic marketing webinar invites go to [MARKETING] instead."
        ),
    },
    {
        "name": "[STRAT]",
        "color": "#2D3748",
        "description": (
            "Vision, Board & Investisseurs — Sujets de gouvernance et vision à "
            "long terme. Inclut rapports pour les investisseurs, préparation du "
            "Board, réflexions stratégiques annuelles, levées de fonds."
        ),
        "keywords": [
            "Conseil d'administration", "Levée de fonds", "Actionnaires",
            "Vision 2026", "Board meeting", "Investor report", "Cap table",
            "Valorisation", "Due diligence", "Term sheet", "Fundraising",
            "Gouvernance", "AGO", "Assemblée générale", "Stratégie",
        ],
        "prompt_hint": (
            "Assign when the email discusses board meetings, investor relations, "
            "fundraising, cap table, governance, or long-term strategic vision. "
            "Senders are typically board members, investors, VCs, or advisors. "
            "Day-to-day financial operations go to [FINANCE] instead."
        ),
    },
    {
        "name": "[FINANCE]",
        "color": "#718096",
        "description": (
            "Gestion Financière & Légal — Santé financière de l'entreprise et "
            "documents contractuels. Inclut rapports de trésorerie (Cash-flow), "
            "bilans, contrats juridiques, audits, conformité et fiscalité."
        ),
        "keywords": [
            "Invoice", "P&L", "Kbis", "Expert-comptable", "Statuts",
            "Facture", "Trésorerie", "Cash-flow", "Bilan", "Audit",
            "Conformité", "RGPD", "Contrat", "Avenant", "Juridique",
            "Comptabilité", "TVA", "Déclaration fiscale",
        ],
        "prompt_hint": (
            "Assign when the email concerns invoices, financial reports, legal "
            "contracts, audits, tax declarations, compliance, or accountant "
            "communications. Senders are typically accountants, lawyers, banks, "
            "or internal finance team. Investor-level finance goes to [STRAT]."
        ),
    },
    {
        "name": "[EQUIPE]",
        "color": "#D69E2E",
        "description": (
            "RH, Culture & Management — Tout ce qui concerne le capital humain. "
            "Inclut recrutements de profils clés, feedbacks d'employés, culture "
            "d'entreprise, annonces internes, et gestion des performances."
        ),
        "keywords": [
            "Onboarding", "Candidature", "Entretien", "Team building",
            "Performance review", "Recrutement", "CV", "Offre d'emploi",
            "Congés", "Démission", "Promotion", "Formation",
            "Culture d'entreprise", "Feedback employé", "1-on-1",
        ],
        "prompt_hint": (
            "Assign when the email is about hiring, HR processes, team culture, "
            "employee feedback, onboarding, performance reviews, or internal "
            "announcements about people. Senders are typically HR, recruiters, "
            "hiring platforms, or team leads discussing people matters."
        ),
    },
    {
        "name": "[PRODUIT]",
        "color": "#00B5D8",
        "description": (
            "R&D & Innovation — Évolution de la roadmap produit et veille "
            "technologique. Inclut nouvelles fonctionnalités IA, recherches sur "
            "les LLM, architecture logicielle globale, et innovations."
        ),
        "keywords": [
            "Roadmap", "Beta", "Nouvelle feature", "R&D", "Innovation",
            "LLM", "GPT", "Machine Learning", "IA", "Prototype",
            "Proof of concept", "POC", "Technical debt", "Benchmark",
            "State of the art", "Research paper", "Veille technologique",
        ],
        "prompt_hint": (
            "Assign when the email discusses product roadmap evolution, R&D "
            "initiatives, AI/LLM research, new feature ideation, or technology "
            "benchmarking. This is about WHAT to build next, not HOW current "
            "projects are going (that's [PROJETS])."
        ),
    },
    {
        "name": "[VENTES]",
        "color": "#E53E3E",
        "description": (
            "Pipeline & Nouveau Business — Flux entrant de nouvelles opportunités "
            "commerciales. Inclut notifications du CRM, nouveaux leads qualifiés, "
            "propositions commerciales envoyées, et négociations en cours."
        ),
        "keywords": [
            "Lead", "Nouveau prospect", "Devis", "Deal", "Opportunité",
            "Proposition commerciale", "RFP", "RFQ", "Pipeline",
            "Closing", "Négociation", "Demo request", "Pricing",
            "Qualification", "Inbound", "Outbound",
        ],
        "prompt_hint": (
            "Assign when the email is about new business opportunities, sales "
            "pipeline, incoming leads, commercial proposals, or deal negotiations. "
            "Once a deal is closed and they become a client, use [CLIENTS] instead. "
            "CRM notifications about new leads also belong here."
        ),
    },
    {
        "name": "[VOYAGES]",
        "color": "#4FD1C5",
        "description": (
            "Logistique de Déplacement — Organisation des déplacements "
            "professionnels. Inclut billets d'avion/train, réservations d'hôtels, "
            "locations de voiture, visas, et confirmations de voyage."
        ),
        "keywords": [
            "Confirmation de vol", "Booking", "Check-in", "Boarding pass",
            "Hébergement", "Réservation hôtel", "Billet d'avion", "Visa",
            "Location voiture", "Itinéraire", "E-ticket", "Airbnb",
            "Expedia", "Booking.com", "Air Canada", "Train",
        ],
        "prompt_hint": (
            "Assign when the email contains travel bookings, flight confirmations, "
            "hotel reservations, car rentals, visa applications, or any travel "
            "logistics. Look for booking reference numbers, itineraries, and "
            "travel agency / airline sender domains."
        ),
    },
    {
        "name": "[TECH-OPS]",
        "color": "#F56565",
        "description": (
            "Alertes & Maintenance — Notifications automatiques des systèmes et "
            "de l'infrastructure. Inclut alertes serveurs, notifications GitHub, "
            "rapports de bugs critiques, et monitoring de production."
        ),
        "keywords": [
            "Alert", "Status", "Deployment failed", "Security vulnerability",
            "System maintenance", "Downtime", "Incident", "Monitoring",
            "CPU", "Memory", "Disk space", "SSL", "Certificate",
            "GitHub", "CI/CD", "Pipeline failed", "Error rate",
        ],
        "prompt_hint": (
            "Assign when the email is an automated system notification — server "
            "alerts, CI/CD pipeline results, security advisories, SSL expirations, "
            "uptime monitoring, or GitHub notifications. The sender is typically a "
            "no-reply address from a DevOps/monitoring tool."
        ),
    },
    {
        "name": "[MARKETING]",
        "color": "#9F7AEA",
        "description": (
            "Newsletters & Veille — Contenu informatif externe et prospection "
            "subie. Inclut newsletters sectorielles, emails marketing, veille "
            "concurrentielle. Tout email contenant 'Unsubscribe' ou 'Se désabonner' "
            "va ici par défaut."
        ),
        "keywords": [
            "Newsletter", "Unsubscribe", "Se désabonner", "Marketing",
            "Promotion", "Offre spéciale", "Webinar invitation",
            "Content marketing", "Blog post", "Industry report",
            "Veille", "Benchmark report", "Market trends",
        ],
        "prompt_hint": (
            "Assign when the email is a newsletter, marketing blast, promotional "
            "offer, or unsolicited vendor outreach. A strong signal is the presence "
            "of 'Unsubscribe' or 'Se désabonner' links. Also assign for industry "
            "news digests and competitive intelligence newsletters."
        ),
    },
    {
        "name": "[SUIVI]",
        "color": "#ECC94B",
        "description": (
            "En attente de réponse — Emails où le CEO attend une action d'un "
            "tiers. Inclut emails envoyés par le CEO avec lui-même en CC/BCC, "
            "relances automatiques. Permet de lister les dossiers en attente de retour."
        ),
        "keywords": [
            "Relance", "Follow-up", "En attente", "Rappel",
            "Suite à mon email", "Avez-vous eu le temps", "Pending",
            "Awaiting response", "Reminder", "Just checking in",
            "Any update", "Mise à jour demandée",
        ],
        "prompt_hint": (
            "Assign when the email is a follow-up where the CEO (or someone on "
            "his behalf) is waiting for a response from a third party. Key signals: "
            "the CEO is in CC/BCC of his own sent email, or the email is a reminder / "
            "follow-up asking for a pending deliverable or answer."
        ),
    },
    {
        "name": "[ADMIN]",
        "color": "#A0AEC0",
        "description": (
            "Administratif Courant — Gestion quotidienne du bureau et fournitures. "
            "Inclut factures d'électricité, assurance des locaux, abonnements "
            "divers, logistique mineure, et services de bureau."
        ),
        "keywords": [
            "Fournitures", "Bail", "Internet", "Télécom", "Entretien locaux",
            "Assurance", "Électricité", "Abonnement", "Bureau",
            "Nettoyage", "Sécurité locaux", "Loyer", "Charges",
            "Photocopieur", "Maintenance bureau",
        ],
        "prompt_hint": (
            "Assign when the email is about office administration — utility bills, "
            "office supplies, lease/rent, insurance, cleaning services, telecom "
            "subscriptions, or minor logistics. This is the catch-all for mundane "
            "operational emails that don't fit other categories."
        ),
    },
]


def seed_smart_labels(db: Session, tenant_id: str) -> None:
    """Create CEO inbox categories if they don't already exist for this tenant."""
    created = 0
    skipped = 0

    for cat in CEO_INBOX_CATEGORIES:
        existing = db.query(SmartLabel).filter(
            SmartLabel.name == cat["name"],
            SmartLabel.tenant_id == tenant_id,
            SmartLabel.parent_id.is_(None),
        ).first()

        if existing:
            skipped += 1
            continue

        label = SmartLabel(
            name=cat["name"],
            color=cat["color"],
            description=cat["description"],
            keywords=cat["keywords"],
            prompt_hint=cat["prompt_hint"],
            tenant_id=tenant_id,
            created_by="system-seed",
        )
        db.add(label)
        created += 1

    if created:
        db.commit()

    logger.info(
        "smart_labels_seeded",
        tenant_id=tenant_id,
        created=created,
        skipped=skipped,
    )
