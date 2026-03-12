"""Seed data for Bob's Control Center — multi-dimensional architecture.

Seeds:
  Layer 1: Industry (Digital Transformation), Career (Sales Rep),
           SkillTemplate (Prospection), TaskTemplate (Email Marketing)
  Layer 2: Organization (The Croo Group) → Dept (Sales) → Team (Digital Experience) → Role (Sales Rep)
  Layer 3: Profile (Canada/QC/MTL), Regulations (CASL, Loi 25)

Idempotent: skips if The Croo Group organization already exists.
"""

import structlog
from sqlalchemy.orm import Session

from app.domain.entities.bcc_entities import (
    BccRole, BccSkill, BccTask, BccTaskStep, BccResource, BccMilestone,
    BccOrganization, BccOrgProfile, BccDepartment, BccTeam,
    BccIndustry, BccCareer, BccSkillTemplate, BccTaskTemplate,
    BccRegulation, BccOrgIndustry, BccRoleCareer, BccRoleSkill, BccRoleTask,
)

logger = structlog.get_logger(__name__)


def _get_or_create(db: Session, model, tenant_id: str, name: str, **kwargs):
    """Get existing record by name or create a new one. Ensures idempotency."""
    existing = db.query(model).filter(
        model.name == name,
        model.tenant_id == tenant_id,
    ).first()
    if existing:
        logger.info("bcc_seed_item_exists", model=model.__tablename__, name=name)
        return existing, False
    obj = model(name=name, tenant_id=tenant_id, **kwargs)
    db.add(obj)
    db.flush()
    return obj, True


def seed_bcc(db: Session, tenant_id: str = "default") -> None:
    """Seed the full multi-dimensional BCC structure."""
    # Idempotent check for organization (Layer 2)
    existing = db.query(BccOrganization).filter(
        BccOrganization.name == "The Croo Group",
        BccOrganization.tenant_id == tenant_id,
    ).first()

    if existing:
        logger.info("bcc_seed_already_exists", org="The Croo Group")
        return

    # ═══════════════════════════════════════════════════════════
    # LAYER 1 — LIBRARY
    # ═══════════════════════════════════════════════════════════

    # ── Industry ──────────────────────────────────────────────
    industry, _ = _get_or_create(
        db, BccIndustry, tenant_id,
        name="Digital Transformation",
        description="Best practices for companies undergoing digital transformation. "
                    "Defines the environment in which Bob operates — agile methodologies, "
                    "cloud-first strategies, data-driven decision making.",
        best_practices={
            "methodology": "Agile / Lean",
            "stack": "Cloud-first SaaS",
            "decision_making": "Data-driven",
            "culture": "Innovation-oriented",
            "market_trends": [
                "AI-powered automation replacing manual workflows",
                "Low-code/no-code platforms democratizing development",
                "Data privacy becoming a competitive advantage (GDPR, Loi 25, CCPA)",
                "Remote-first teams driving cloud collaboration tool adoption",
                "Customer experience (CX) as the primary differentiator",
            ],
            "competitive_landscape": {
                "crm_leaders": ["Salesforce", "HubSpot", "Microsoft Dynamics"],
                "croo_differentiators": [
                    "AI-native from day one (Bob assistant)",
                    "Voice-first interaction model",
                    "Automated pipeline intelligence",
                    "Canadian-built, privacy-compliant by design",
                ],
            },
            "key_terminology": {
                "ARR": "Annual Recurring Revenue",
                "MRR": "Monthly Recurring Revenue",
                "CAC": "Customer Acquisition Cost",
                "LTV": "Lifetime Value",
                "NRR": "Net Revenue Retention",
                "PLG": "Product-Led Growth",
                "SaaS": "Software as a Service",
                "ICP": "Ideal Customer Profile",
            },
            "kpis": {
                "saas_benchmarks": {
                    "ltv_cac_ratio": "> 3:1",
                    "net_revenue_retention": "> 110%",
                    "gross_margin": "> 70%",
                    "magic_number": "> 0.75",
                },
            },
            "regulatory_context": [
                "CASL (Canada): Express consent for commercial emails",
                "Loi 25 (Québec): Privacy framework, consent required",
                "PIPEDA (Canada): Federal privacy law",
                "SOC 2 Type II: Security compliance for SaaS",
            ],
        },
    )

    # ── Career ────────────────────────────────────────────────
    career, _ = _get_or_create(
        db, BccCareer, tenant_id,
        name="Sales Rep",
        description="Professional B2B SaaS sales representative — the toolkit for selling "
                    "technology solutions to businesses. Covers the full sales cycle from "
                    "prospecting to closing, with emphasis on consultative and value-based selling.",
        typical_skills=[
            "Prospection & Lead Qualification",
            "Email Writing & Outreach",
            "Solution Demo & Value Selling",
            "Negotiation & Closing",
            "CRM Mastery",
            "Account Management & Expansion",
            "Active Listening",
            "Objection Handling",
            "Business Acumen",
            "Time Management",
        ],
        typical_tasks=[
            "Pipeline Review & CRM Hygiene (daily)",
            "Outbound Prospecting Block (daily)",
            "Email Campaign — Nurture Sequence (weekly)",
            "Discovery Call + Product Demo (daily)",
            "Deal Negotiation & Close (weekly)",
            "Quarterly Business Review (quarterly)",
            "Competitive Intelligence Research (monthly)",
        ],
    )

    # ── Skill Template ────────────────────────────────────────
    skill_tpl, _ = _get_or_create(
        db, BccSkillTemplate, tenant_id,
        name="Prospection",
        type="hard",
        description="Ability to identify, contact and qualify potential B2B leads for SaaS CRM sales. "
                    "Includes ICP definition, multi-channel outreach (email, LinkedIn, phone), "
                    "lead scoring using BANT/MEDDIC frameworks, and pipeline building.",
        category="Sales",
    )

    # ── Task Template ─────────────────────────────────────────
    task_tpl, _ = _get_or_create(
        db, BccTaskTemplate, tenant_id,
        name="Email Marketing",
        description="Design and execute targeted email campaigns to nurture leads and drive engagement. "
                    "Includes audience segmentation, content creation, A/B testing, and performance tracking.",
        context={
            "expectations": "Send targeted, personalized email campaigns respecting jurisdiction regulations. "
                           "Each campaign must be CASL-compliant with proper consent management.",
            "deliverables": [
                "Campaign plan with audience segmentation",
                "Email copy (subject + body + CTA)",
                "Segment list from CRM",
                "A/B test configuration",
                "Performance report",
            ],
            "success_metrics": {
                "open_rate": "> 20%",
                "click_rate": "> 3%",
                "reply_rate": "> 1%",
                "unsubscribe_rate": "< 0.5%",
                "bounce_rate": "< 2%",
            },
            "standard_operating_procedure": [
                "1. Review last campaign performance",
                "2. Segment audience based on engagement + stage",
                "3. Draft email content aligned with campaign goal",
                "4. Run content through Bob AI for tone/compliance review",
                "5. Set up A/B test (subject line or CTA)",
                "6. Schedule send (Tue-Thu, 9-11 AM recipient time)",
                "7. Monitor real-time metrics for first 2 hours",
                "8. Document results and insights",
            ],
            "compliance_requirements": [
                "CASL: Express consent required — no cold email to Canadian contacts without prior consent",
                "Include sender identification (company name + address)",
                "Functional unsubscribe mechanism in every email",
                "No misleading subject lines or sender names",
                "Respect Loi 25 data privacy requirements",
            ],
            "tools_required": [
                "Croo Digital Experience (CRM + email)",
                "Bob AI (content review + compliance check)",
            ],
        },
        frequency="weekly",
        category="Marketing",
        required_skill_ids=[],
    )

    # ═══════════════════════════════════════════════════════════
    # LAYER 2 — ORGANIZATION HIERARCHY
    # ═══════════════════════════════════════════════════════════

    # ── Organization ──────────────────────────────────────────
    org = BccOrganization(
        name="The Croo Group",
        description="Parent organization with multiple sub-organizations.",
        icon="fa-solid fa-building",
        color="#FF4500",
        tenant_id=tenant_id,
    )
    db.add(org)
    db.flush()

    # ── Profile ───────────────────────────────────────────────
    profile = BccOrgProfile(
        organization_id=org.id,
        country="Canada",
        state_province="Québec",
        city="Montréal",
        operations_domains=["Digital Transformation", "Technology", "Consulting"],
        tenant_id=tenant_id,
    )
    db.add(profile)
    db.flush()

    # ── Department ────────────────────────────────────────────
    dept = BccDepartment(
        organization_id=org.id,
        name="Sales",
        description="Sales department — responsible for revenue generation.",
        tenant_id=tenant_id,
    )
    db.add(dept)
    db.flush()

    # ── Team ──────────────────────────────────────────────────
    team = BccTeam(
        department_id=dept.id,
        name="Digital Experience",
        description="Team focused on digital sales channels and customer experience.",
        tenant_id=tenant_id,
    )
    db.add(team)
    db.flush()

    # ── Role (under team) ────────────────────────────────────
    role = BccRole(
        team_id=team.id,
        name="Sales Rep",
        department="Sales",
        description="B2B sales representative — prospecting, qualification, demos and closing.",
        icon="fa-solid fa-user-tie",
        color="#FF4500",
        tenant_id=tenant_id,
    )
    db.add(role)
    db.flush()

    # ═══════════════════════════════════════════════════════════
    # LAYER 3 — CONTEXT RESOLUTION (LINKS + REGULATIONS)
    # ═══════════════════════════════════════════════════════════

    # ── Org ↔ Industry link ───────────────────────────────────
    db.add(BccOrgIndustry(
        organization_id=org.id,
        industry_id=industry.id,
        tenant_id=tenant_id,
    ))

    # ── Role ↔ Career link ────────────────────────────────────
    db.add(BccRoleCareer(
        role_id=role.id,
        career_id=career.id,
        tenant_id=tenant_id,
    ))

    # ── Role ↔ Skill Template link ────────────────────────────
    db.add(BccRoleSkill(
        role_id=role.id,
        skill_template_id=skill_tpl.id,
        tenant_id=tenant_id,
    ))

    # ── Role ↔ Task Template link ─────────────────────────────
    db.add(BccRoleTask(
        role_id=role.id,
        task_template_id=task_tpl.id,
        tenant_id=tenant_id,
    ))

    # ── Regulations ───────────────────────────────────────────
    regulations = [
        BccRegulation(
            profile_id=profile.id,
            name="CASL — Canada's Anti-Spam Legislation",
            description="Requires express consent before sending commercial electronic messages. "
                        "Applies to emails, SMS, and social media messages.",
            type="marketing",
            scope="country",
            enforcement_level="mandatory",
            details={
                "jurisdiction": "Canada",
                "key_rules": [
                    "Express consent required for commercial emails",
                    "Unsubscribe mechanism mandatory",
                    "Sender identification required",
                    "No misleading subject lines",
                ],
                "penalties": "Up to $10M per violation",
            },
            tenant_id=tenant_id,
        ),
        BccRegulation(
            profile_id=profile.id,
            name="Loi 25 — Québec Privacy Law",
            description="Modernized privacy framework for Québec. Requires consent for "
                        "personal information collection and use, privacy impact assessments.",
            type="privacy",
            scope="state",
            enforcement_level="mandatory",
            details={
                "jurisdiction": "Québec, Canada",
                "key_rules": [
                    "Explicit consent for personal data collection",
                    "Privacy impact assessments required",
                    "Data portability rights",
                    "Breach notification within 72 hours",
                ],
            },
            tenant_id=tenant_id,
        ),
        BccRegulation(
            profile_id=profile.id,
            name="Professional Conduct — Regulated Professions",
            description="Certain professions are regulated by professional orders. "
                        "Only licensed professionals can use certain titles or give specific advice.",
            type="professional",
            scope="state",
            enforcement_level="mandatory",
            details={
                "jurisdiction": "Québec, Canada",
                "examples": [
                    "Only lawyers can give legal advice",
                    "Only CPAs can sign audit reports",
                    "Only engineers can seal plans",
                ],
            },
            tenant_id=tenant_id,
        ),
    ]
    for reg in regulations:
        db.add(reg)

    db.flush()

    # ═══════════════════════════════════════════════════════════
    # ROLE DATA — Skills, Tasks, Resources, Milestones
    # Context: Sales Rep selling Croo Digital Experience (automated CRM)
    # ═══════════════════════════════════════════════════════════

    # ── Skills ────────────────────────────────────────────────

    skill_crm = BccSkill(
        role_id=role.id,
        name="CRM Mastery — Croo Digital Experience",
        type="tool",
        stage="onboarding",
        priority=5,
        description="Master the Croo Digital Experience platform from the inside. "
                    "Learn every module: contacts, organizations, opportunities, pipelines, "
                    "analytics, Bob AI assistant, automations. You sell what you breathe.",
        prerequisites=[],
        training_data={
            "learning_objectives": [
                "Navigate all CRM modules autonomously",
                "Create and manage contacts, organizations, and opportunities",
                "Configure and use pipeline stages effectively",
                "Leverage Bob AI for daily sales tasks",
                "Set up automations for repetitive workflows",
                "Read and interpret analytics dashboards",
            ],
            "sub_skills": [
                "Contact Management", "Organization Management",
                "Opportunity Pipeline", "Activity Tracking",
                "Dashboard & Analytics", "Bob AI Interaction",
                "Automation Setup", "Quote Generation",
            ],
            "crm_modules_used": [
                {"module": "contacts", "usage": "Create, search, segment contacts. Import from CSV."},
                {"module": "organizations", "usage": "Link contacts to companies. Track hierarchy."},
                {"module": "opportunities", "usage": "Full pipeline lifecycle from lead to close."},
                {"module": "tasks", "usage": "Schedule follow-ups, log calls, manage activities."},
                {"module": "analytics", "usage": "Review performance dashboards and KPIs."},
                {"module": "bob_assistant", "usage": "Voice and chat interactions for AI-assisted tasks."},
            ],
            "bob_conversation_starters": [
                "Bob, montre-moi comment créer un contact à partir d'un email reçu",
                "Bob, comment je configure un pipeline personnalisé?",
                "Bob, quelles sont mes opportunités qui stagnent depuis plus de 7 jours?",
                "Bob, génère un rapport de mes activités de la semaine",
                "Bob, aide-moi à comprendre le tableau de bord analytics",
            ],
            "assessment_criteria": {
                "navigation": "Navigate to any module in < 3 seconds",
                "data_entry": "Create a complete contact + opportunity in < 2 minutes",
                "pipeline": "Maintain 100% pipeline accuracy for 5 consecutive days",
                "bob_usage": "Complete 3+ tasks using Bob AI assistance",
                "automation": "Set up at least 1 workflow automation",
            },
            "key_concepts": {
                "Pipeline Stages": "Lead → Qualified → Demo → Proposal → Negotiation → Closed Won/Lost",
                "Contact vs Organization": "Contacts are people, Organizations are companies. Always link both.",
                "Activity Logging": "Every call, email, and meeting must be logged for AI analysis.",
                "Bob AI": "Voice-first AI assistant that analyzes your pipeline and suggests actions.",
            },
        },
        tenant_id=tenant_id,
    )
    db.add(skill_crm)

    skill_prospect = BccSkill(
        role_id=role.id,
        name="Prospection & Lead Qualification",
        type="hard",
        stage="foundation",
        priority=5,
        description="Identify and qualify potential B2B clients who need CRM automation. "
                    "Build ICP (Ideal Customer Profile), use LinkedIn Sales Navigator, "
                    "research companies undergoing digital transformation, score leads "
                    "using BANT (Budget, Authority, Need, Timeline).",
        prerequisites=["CRM Mastery"],
        training_data={
            "learning_objectives": [
                "Define and articulate the Ideal Customer Profile (ICP)",
                "Score leads using BANT and MEDDIC frameworks",
                "Use LinkedIn Sales Navigator for targeted prospecting",
                "Research companies and identify digital transformation signals",
                "Build a qualified pipeline of 50+ leads in 4 weeks",
            ],
            "sub_skills": [
                "ICP Definition", "Lead Scoring (BANT)",
                "LinkedIn Sales Navigator", "Company Research",
                "Signal Detection", "Lead Enrichment",
                "First Touch Personalization",
            ],
            "crm_modules_used": [
                {"module": "contacts", "usage": "Search and filter leads by ICP criteria. Enrich contact data."},
                {"module": "organizations", "usage": "Research target companies. Track industry and size."},
                {"module": "opportunities", "usage": "Create new opportunities from qualified leads."},
                {"module": "bob_assistant", "usage": "Ask Bob to analyze CRM data for lead identification."},
            ],
            "bob_conversation_starters": [
                "Bob, analyse mon CRM et identifie les contacts qui matchent notre ICP",
                "Bob, quelles entreprises dans mon pipeline sont en transformation digitale?",
                "Bob, score ce lead selon les critères BANT",
                "Bob, rédige un message de premier contact pour ce prospect",
                "Bob, montre-moi les leads inactifs qui méritent un suivi",
            ],
            "assessment_criteria": {
                "icp_mastery": "Can articulate ICP in 30 seconds",
                "lead_scoring": "Correctly score 10 leads using BANT",
                "pipeline_volume": "50+ qualified leads in pipeline",
                "outreach_volume": "200+ touchpoints completed in first month",
                "conversion_rate": "Lead-to-qualified rate > 15%",
            },
            "key_concepts": {
                "ICP": "Ideal Customer Profile: >10 employees, B2B, active sales team, manual CRM or spreadsheets",
                "BANT": "Budget ($500-5000/mo), Authority (VP Sales/CEO), Need (manual processes), Timeline (this quarter)",
                "MEDDIC": "Metrics, Economic buyer, Decision criteria, Decision process, Identify pain, Champion",
                "Signal Detection": "Job postings for sales roles, new funding, tech stack changes, CRM complaints on social",
            },
        },
        tenant_id=tenant_id,
    )
    db.add(skill_prospect)

    skill_email = BccSkill(
        role_id=role.id,
        name="Email Writing & Outreach",
        type="hard",
        stage="foundation",
        priority=4,
        description="Write compelling cold emails, follow-up sequences, and nurture campaigns. "
                    "Personalize at scale using CRM data. Respect CASL and Loi 25 compliance "
                    "requirements for Canadian market.",
        prerequisites=["CRM Mastery"],
        training_data={
            "learning_objectives": [
                "Write cold emails with > 20% open rate",
                "Design multi-step follow-up sequences",
                "Personalize emails at scale using CRM data",
                "Ensure 100% CASL compliance on every email",
                "Use Bob AI for copy review and tone optimization",
            ],
            "sub_skills": [
                "Subject Line Craft", "Personalization at Scale",
                "Follow-up Sequencing", "CTA Design",
                "CASL Compliance", "A/B Testing",
                "Email Deliverability",
            ],
            "crm_modules_used": [
                {"module": "contacts", "usage": "Pull recipient data for personalization. Check consent status."},
                {"module": "tasks", "usage": "Schedule follow-ups. Track email activities."},
                {"module": "bob_assistant", "usage": "Review email copy for tone, compliance, and effectiveness."},
            ],
            "bob_conversation_starters": [
                "Bob, rédige un cold email pour un DG qui utilise encore des spreadsheets",
                "Bob, est-ce que cet email est conforme CASL?",
                "Bob, crée une séquence de 5 emails de nurture pour nos leads qualifiés",
                "Bob, optimise cette ligne de sujet pour un meilleur taux d'ouverture",
                "Bob, quel est le meilleur moment pour envoyer cet email?",
            ],
            "assessment_criteria": {
                "open_rate": "Achieve > 20% open rate on cold emails",
                "reply_rate": "Achieve > 3% reply rate",
                "compliance": "100% CASL compliant emails",
                "personalization": "Each email references at least 2 prospect-specific details",
                "sequence_design": "Design a complete 5-step nurture sequence",
            },
            "key_concepts": {
                "CASL": "Express consent required. Sender ID. Unsubscribe mechanism. No misleading headers.",
                "Personalization": "Use company name, recent news, tech stack, pain points from research.",
                "Sequence Cadence": "Day 1 → Day 3 → Day 7 → Day 14 → Day 21 (break-up email)",
                "Email Templates": "Initial outreach, trigger-based, case study, ROI calculator, break-up",
            },
        },
        tenant_id=tenant_id,
    )
    db.add(skill_email)

    skill_demo = BccSkill(
        role_id=role.id,
        name="Solution Demo & Value Selling",
        type="hard",
        stage="practice",
        priority=5,
        description="Deliver compelling product demonstrations of Croo Digital Experience. "
                    "Focus on automation ROI: time saved on data entry, AI-powered insights, "
                    "automated follow-ups. Map features to customer pain points. "
                    "Use the Challenger Sale methodology.",
        prerequisites=["CRM Mastery", "Prospection"],
        training_data={
            "learning_objectives": [
                "Deliver a structured 30-minute discovery + demo",
                "Map product features to prospect pain points",
                "Calculate and present ROI metrics",
                "Handle objections during live demos",
                "Use Challenger Sale methodology",
            ],
            "sub_skills": [
                "Discovery Questions", "Feature-to-Benefit Mapping",
                "ROI Calculation", "Live Demo Delivery",
                "Objection Handling (live)", "Challenger Sale",
                "Storytelling with Data",
            ],
            "crm_modules_used": [
                {"module": "opportunities", "usage": "Demo the full pipeline lifecycle. Show automation."},
                {"module": "analytics", "usage": "Show real-time dashboards and KPI tracking."},
                {"module": "bob_assistant", "usage": "Demo Bob's AI capabilities live — voice mode, smart suggestions."},
                {"module": "contacts", "usage": "Show contact enrichment and search capabilities."},
            ],
            "bob_conversation_starters": [
                "Bob, prépare-moi un brief pour ma démo avec [Company Name]",
                "Bob, quels sont les pain points typiques d'une entreprise de cette taille?",
                "Bob, calcule le ROI pour une équipe de 10 sales reps",
                "Bob, quels features dois-je mettre en avant pour un prospect en transformation digitale?",
                "Bob, simule une objection 'on a déjà un CRM' pour que je m'entraîne",
            ],
            "assessment_criteria": {
                "demo_delivery": "Complete a structured demo in 30 minutes",
                "roi_presentation": "Present ROI calculations with concrete numbers",
                "objection_handling": "Handle 3+ live objections smoothly",
                "conversion": "Convert 30% of demos to next step",
                "feedback_score": "Average prospect feedback score > 4/5",
            },
            "key_concepts": {
                "Demo Flow": "10 min discovery → 15 min tailored demo → 5 min next steps",
                "Challenger Sale": "Teach-Tailor-Take Control. Reframe the prospect's thinking.",
                "ROI Calculator": "Hours saved/rep/week × rep count × hourly cost = annual savings",
                "Live vs Recorded": "Always prefer live demos. Recorded only for follow-up.",
            },
        },
        tenant_id=tenant_id,
    )
    db.add(skill_demo)

    skill_nego = BccSkill(
        role_id=role.id,
        name="Negotiation & Closing",
        type="soft",
        stage="practice",
        priority=4,
        description="Handle objections (price, integration, change management), build "
                    "business cases with ROI calculations, negotiate SaaS contracts "
                    "(annual vs monthly, seat count, onboarding packages). "
                    "Use urgency without pressure.",
        prerequisites=["Solution Demo"],
        training_data={
            "learning_objectives": [
                "Handle the top 10 CRM objections confidently",
                "Build business cases with ROI calculations",
                "Negotiate SaaS contracts (annual vs monthly, seat tiers)",
                "Create urgency without aggressive pressure",
                "Close deals with clear mutual action plans",
            ],
            "sub_skills": [
                "Objection Handling", "Business Case Building",
                "Contract Negotiation", "Pricing Strategy",
                "Mutual Action Plans", "Urgency Creation",
                "Stakeholder Alignment",
            ],
            "crm_modules_used": [
                {"module": "opportunities", "usage": "Track deal stages. Move to Negotiation/Closed Won."},
                {"module": "contacts", "usage": "Identify decision makers and champions."},
                {"module": "bob_assistant", "usage": "Ask Bob for objection responses and pricing recommendations."},
            ],
            "bob_conversation_starters": [
                "Bob, prépare-moi un business case ROI pour cette opportunité",
                "Bob, comment répondre à l'objection 'c'est trop cher'?",
                "Bob, quelles sont les meilleures options de pricing pour 15 users?",
                "Bob, génère un mutual action plan pour closer ce deal",
                "Bob, analyse les deals que j'ai perdus — quelles patterns vois-tu?",
            ],
            "assessment_criteria": {
                "close_rate": "Close rate > 30%",
                "objection_handling": "Handle 5+ different objections with confidence",
                "deal_size": "Average deal size > $5,000 ARR",
                "negotiation_time": "Average negotiation stage < 14 days",
                "business_case": "Build a complete ROI business case",
            },
            "key_concepts": {
                "Top Objections": "'We already have a CRM', 'Too expensive', 'Team won't adopt', 'Need X integration'",
                "Pricing Models": "Monthly ($49/user) vs Annual ($39/user) — 20% discount for commitment",
                "Mutual Action Plan": "Shared timeline with prospect: trial → eval → decision → onboarding",
                "Cost of Inaction": "Calculate what NOT switching costs them monthly",
            },
        },
        tenant_id=tenant_id,
    )
    db.add(skill_nego)

    skill_account = BccSkill(
        role_id=role.id,
        name="Account Management & Expansion",
        type="soft",
        stage="mastery",
        priority=3,
        description="Build long-term relationships with existing clients. Identify upsell "
                    "and cross-sell opportunities (additional seats, premium features, "
                    "integrations). Drive adoption and reduce churn. Become a trusted advisor "
                    "in their digital transformation journey.",
        prerequisites=["Negotiation", "Solution Demo"],
        training_data={
            "learning_objectives": [
                "Identify upsell and cross-sell opportunities in existing accounts",
                "Drive product adoption and reduce churn",
                "Conduct Quarterly Business Reviews (QBRs)",
                "Build champion relationships within customer organizations",
                "Generate referrals from satisfied customers",
            ],
            "sub_skills": [
                "Account Health Monitoring", "Upsell Identification",
                "QBR Facilitation", "Churn Prevention",
                "Champion Building", "Referral Generation",
                "Expansion Revenue",
            ],
            "crm_modules_used": [
                {"module": "organizations", "usage": "Track account health, usage, and expansion signals."},
                {"module": "opportunities", "usage": "Create expansion opportunities (upsell/cross-sell)."},
                {"module": "contacts", "usage": "Map stakeholders and identify champions."},
                {"module": "analytics", "usage": "Review account-level analytics and usage data."},
                {"module": "bob_assistant", "usage": "Ask Bob for churn risk analysis and expansion suggestions."},
            ],
            "bob_conversation_starters": [
                "Bob, quels comptes montrent des signes de churn?",
                "Bob, identifie les opportunités d'upsell dans mes comptes actifs",
                "Bob, prépare un agenda de QBR pour [Company Name]",
                "Bob, quels comptes n'ont pas eu de contact depuis 30 jours?",
                "Bob, génère un rapport d'adoption pour mes 5 plus gros comptes",
            ],
            "assessment_criteria": {
                "expansion_revenue": "Close 1+ upsell or cross-sell per quarter",
                "churn_rate": "Maintain churn rate < 5% annual",
                "nrr": "Net Revenue Retention > 110%",
                "qbr_completion": "Conduct QBR with 100% of strategic accounts",
                "referral": "Generate 1+ qualified referral per quarter",
            },
            "key_concepts": {
                "NRR": "Net Revenue Retention — expansion revenue minus churn. Target > 110%.",
                "QBR": "Quarterly Business Review — structured check-in on goals, adoption, roadmap.",
                "Champion": "Internal advocate who pushes for your product adoption.",
                "Health Score": "Login frequency + feature adoption + support tickets + NPS.",
            },
        },
        tenant_id=tenant_id,
    )
    db.add(skill_account)

    db.flush()

    # ── Resources ─────────────────────────────────────────────

    resources = [
        BccResource(
            skill_id=skill_crm.id,
            title="Croo Digital Experience — Internal Documentation",
            type="documentation",
            content="Complete product documentation covering all modules, API, and admin features.",
            url="https://docs.croo.digital",
            tenant_id=tenant_id,
        ),
        BccResource(
            skill_id=skill_crm.id,
            title="Bob AI — Best Practices for Sales Teams",
            type="guide",
            content="How to leverage Bob's AI assistant for prospecting, email drafting, and pipeline analysis.",
            tenant_id=tenant_id,
        ),
        BccResource(
            skill_id=skill_prospect.id,
            title="ICP Worksheet — Croo's Target Market",
            type="template",
            content="Ideal Customer Profile: > 10 employees, B2B, active sales team, "
                    "currently using manual CRM or spreadsheets, in Digital Transformation sector.",
            tenant_id=tenant_id,
        ),
        BccResource(
            skill_id=skill_prospect.id,
            title="BANT Qualification Framework",
            type="guide",
            content="Budget: CRM budget $500-5000/mo, Authority: VP Sales or CEO, "
                    "Need: manual processes slowing growth, Timeline: evaluating this quarter.",
            tenant_id=tenant_id,
        ),
        BccResource(
            skill_id=skill_email.id,
            title="Cold Email Templates — SaaS CRM",
            type="template",
            content="5 proven email templates for CRM sales: initial outreach, trigger-based, "
                    "case study share, ROI calculator, break-up email.",
            tenant_id=tenant_id,
        ),
        BccResource(
            skill_id=skill_email.id,
            title="CASL Compliance Checklist",
            type="checklist",
            content="Mandatory requirements for commercial emails in Canada: express consent, "
                    "sender ID, unsubscribe mechanism, no false headers.",
            tenant_id=tenant_id,
        ),
        BccResource(
            skill_id=skill_demo.id,
            title="Croo Demo Script — 30-minute Discovery + Demo",
            type="playbook",
            content="Structured demo flow: 10 min discovery, 15 min tailored demo, 5 min next steps. "
                    "Focus on automation ROI and Bob AI differentiators.",
            tenant_id=tenant_id,
        ),
        BccResource(
            skill_id=skill_nego.id,
            title="Objection Handling — Top 10 CRM Objections",
            type="playbook",
            content="Common objections: 'We already have a CRM', 'Too expensive', 'Our team won't adopt it', "
                    "'We need X integration'. Responses with proof points.",
            tenant_id=tenant_id,
        ),
    ]
    for res in resources:
        db.add(res)
    db.flush()

    # ── Tasks ─────────────────────────────────────────────────

    task_pipeline = BccTask(
        role_id=role.id,
        name="Pipeline Review & CRM Hygiene",
        frequency="daily",
        stage="onboarding",
        category="Pipeline Management",
        description="Review your pipeline in Croo Digital Experience every morning. "
                    "Update deal stages, add notes from yesterday's calls, flag stale deals. "
                    "Bob will surface smart suggestions based on AI analysis.",
        training_data={
            "crm_modules_used": [
                {"module": "opportunities", "usage": "Review all deals, update stages, flag stale opportunities."},
                {"module": "tasks", "usage": "Check scheduled activities, prep for today's meetings."},
                {"module": "analytics", "usage": "Review pipeline health dashboards."},
                {"module": "bob_assistant", "usage": "Surface smart suggestions, auto-detect stale deals."},
            ],
            "bob_assistance": [
                "Identifie automatiquement les deals sans activité > 7 jours",
                "Suggère les follow-ups prioritaires basés sur l'analyse AI",
                "Détecte les changements de pipeline et alerte sur les risques",
                "Génère un résumé quotidien de l'état du pipeline",
            ],
            "success_metrics": {
                "pipeline_accuracy": "100% deals à jour chaque matin",
                "stale_deals": "0 deals sans activité > 7 jours non flaggés",
                "notes_coverage": "100% des calls ont des notes dans les 24h",
                "time_to_complete": "< 15 minutes par session",
            },
            "compliance_notes": [
                "Les notes de calls ne doivent contenir aucune donnée personnelle sensible",
                "Respecter la confidentialité des informations partagées en appel",
            ],
            "tools_required": ["Croo Digital Experience — Opportunities tab", "Bob AI — Smart Suggestions"],
        },
        tenant_id=tenant_id,
    )
    db.add(task_pipeline)
    db.flush()

    for i, step in enumerate([
        "Open Croo Digital Experience → Opportunities tab",
        "Review Bob's Smart Suggestions for follow-ups",
        "Update deal stages for any moved opportunities",
        "Add notes from yesterday's calls/meetings",
        "Flag deals with no activity > 7 days",
        "Check today's scheduled activities and prep",
    ], 1):
        db.add(BccTaskStep(task_id=task_pipeline.id, step_number=i, instruction=step))

    task_prospect_daily = BccTask(
        role_id=role.id,
        name="Outbound Prospecting Block",
        frequency="daily",
        stage="foundation",
        category="Prospection",
        description="Dedicated 2-hour block for outbound prospecting. Research target accounts, "
                    "craft personalized outreach, send emails and LinkedIn messages. "
                    "Target: 20 new touchpoints per day.",
        required_skills=["Prospection", "Email Writing"],
        training_data={
            "crm_modules_used": [
                {"module": "contacts", "usage": "Filter leads by ICP. Search for new targets."},
                {"module": "organizations", "usage": "Research target companies. Check existing relationships."},
                {"module": "tasks", "usage": "Log outreach activities. Schedule follow-ups."},
                {"module": "bob_assistant", "usage": "Draft personalized emails. Detect warm leads from replies."},
            ],
            "bob_assistance": [
                "Rédige des cold emails personnalisés basés sur les données CRM",
                "Détecte automatiquement les réponses chaudes pour priorisation",
                "Analyse les contacts CRM pour identifier ceux qui matchent l'ICP",
                "Vérifie la conformité CASL avant envoi",
                "Suggère le meilleur moment d'envoi basé sur les données historiques",
            ],
            "success_metrics": {
                "daily_touchpoints": "20+ touchpoints par jour",
                "email_open_rate": "> 20%",
                "reply_rate": "> 3%",
                "leads_qualified": "5+ leads qualifiés par semaine",
                "casl_compliance": "100%",
            },
            "compliance_notes": [
                "Vérifier le consentement express avant tout email commercial (CASL)",
                "Inclure l'identification de l'expéditeur dans chaque message",
                "Mécanisme de désabonnement fonctionnel obligatoire",
                "Ne pas utiliser de sujets ou noms d'expéditeur trompeurs",
            ],
            "tools_required": [
                "Croo Digital Experience — Contacts & Organizations",
                "Bob AI — Email drafting & compliance",
                "LinkedIn Sales Navigator (externe)",
            ],
        },
        tenant_id=tenant_id,
    )
    db.add(task_prospect_daily)
    db.flush()

    for i, step in enumerate([
        "Pull today's target list from Croo (filtered by ICP criteria)",
        "Research 5-10 companies: recent news, tech stack, growth signals",
        "Draft personalized cold emails using Bob's AI writing assistant",
        "Review emails for CASL compliance (consent, unsubscribe, sender ID)",
        "Send outreach via email and LinkedIn InMail",
        "Log all activities in Croo with next-step dates",
        "Review Bob's reply detection for any warm leads",
    ], 1):
        db.add(BccTaskStep(task_id=task_prospect_daily.id, step_number=i, instruction=step))

    task_email_campaign = BccTask(
        role_id=role.id,
        name="Email Campaign — Nurture Sequence",
        frequency="weekly",
        stage="foundation",
        category="Marketing",
        description="Design and launch weekly email nurture campaigns targeting leads "
                    "in the evaluation phase. Focus on CRM automation pain points, "
                    "ROI case studies, and Croo differentiators. "
                    "All campaigns must comply with CASL.",
        required_skills=["Email Writing"],
        training_data={
            "crm_modules_used": [
                {"module": "contacts", "usage": "Segmenter l'audience par engagement, stage et consentement."},
                {"module": "tasks", "usage": "Planifier les envois. Suivre les résultats."},
                {"module": "analytics", "usage": "Analyser open rate, CTR, replies par campagne."},
                {"module": "bob_assistant", "usage": "Révision du copy, vérification compliance, A/B testing."},
            ],
            "bob_assistance": [
                "Révise le copy pour le ton et la conformité réglementaire",
                "Suggère des lignes de sujet optimisées pour l'ouverture",
                "Analyse les résultats de la campagne précédente",
                "Recommande la segmentation optimale basée sur l'engagement",
                "Génère des variantes A/B pour les tests",
            ],
            "success_metrics": {
                "open_rate": "> 20%",
                "click_rate": "> 3%",
                "reply_rate": "> 1%",
                "unsubscribe_rate": "< 0.5%",
                "bounce_rate": "< 2%",
            },
            "compliance_notes": [
                "CASL : Consentement express requis pour tous les contacts canadiens",
                "Identification de l'expéditeur obligatoire (nom + adresse)",
                "Mécanisme de désabonnement fonctionnel dans chaque email",
                "Pas de lignes de sujet ou noms d'expéditeur trompeurs",
                "Loi 25 : Respecter les exigences de confidentialité des données",
            ],
            "tools_required": [
                "Croo Digital Experience — Contacts & Analytics",
                "Bob AI — Copy review & compliance check",
            ],
        },
        tenant_id=tenant_id,
    )
    db.add(task_email_campaign)
    db.flush()

    for i, step in enumerate([
        "Review campaign performance from last week (open rate, CTR, replies)",
        "Segment audience: new leads vs. warm leads vs. re-engagement",
        "Draft email content: subject line + body + CTA",
        "Ask Bob to review copy for tone and compliance",
        "Schedule campaign send (Tue-Thu, 9-11 AM ET)",
        "Set up A/B test on subject line",
        "Document results in campaign tracker",
    ], 1):
        db.add(BccTaskStep(task_id=task_email_campaign.id, step_number=i, instruction=step))

    task_demo_delivery = BccTask(
        role_id=role.id,
        name="Discovery Call + Product Demo",
        frequency="daily",
        stage="practice",
        category="Sales Execution",
        description="Conduct discovery calls to understand prospect pain points, "
                    "then deliver a tailored Croo Digital Experience demo. "
                    "Highlight automation capabilities, Bob AI, and ROI metrics. "
                    "End with clear next steps and timeline.",
        required_skills=["Solution Demo", "CRM Mastery"],
        training_data={
            "crm_modules_used": [
                {"module": "contacts", "usage": "Pre-call research on prospect. Review history."},
                {"module": "organizations", "usage": "Research company profile, size, industry."},
                {"module": "opportunities", "usage": "Demo pipeline, automation, deal tracking live."},
                {"module": "analytics", "usage": "Show real-time KPI dashboards during demo."},
                {"module": "bob_assistant", "usage": "Demo Bob's voice mode and smart suggestions live."},
            ],
            "bob_assistance": [
                "Prépare un brief pré-appel avec toutes les infos du prospect",
                "Suggère les features à mettre en avant selon le profil",
                "Calcule le ROI en temps réel pendant la démo",
                "Génère les notes de l'appel automatiquement après",
                "Crée le follow-up avec next steps",
            ],
            "success_metrics": {
                "demo_to_next_step": "> 30% conversion to proposal",
                "demo_duration": "30 minutes (10 discovery + 15 demo + 5 next steps)",
                "follow_up_time": "Notes + next steps logged within 1 hour",
                "prospect_feedback": "Average feedback score > 4/5",
            },
            "tools_required": [
                "Croo Digital Experience — Full platform (live demo)",
                "Bob AI — Voice mode & smart suggestions",
                "Screen sharing tool (Zoom/Teams)",
            ],
        },
        tenant_id=tenant_id,
    )
    db.add(task_demo_delivery)
    db.flush()

    for i, step in enumerate([
        "Pre-call prep: review prospect's company, current CRM, pain points",
        "Discovery (10 min): Ask about current processes, team size, pain points",
        "Tailored demo (15 min): Show features mapped to their specific needs",
        "Highlight Bob AI: automated data entry, smart suggestions, voice mode",
        "Show ROI calculator: time saved per rep per week",
        "Next steps (5 min): Timeline, decision makers, trial or proposal",
        "Log call notes and next steps in Croo immediately after",
    ], 1):
        db.add(BccTaskStep(task_id=task_demo_delivery.id, step_number=i, instruction=step))

    task_deal_close = BccTask(
        role_id=role.id,
        name="Deal Negotiation & Close",
        frequency="weekly",
        stage="practice",
        category="Sales Execution",
        description="Manage deals in negotiation stage. Build business cases, "
                    "handle final objections, prepare proposals with pricing options "
                    "(annual vs monthly, seat tiers, onboarding packages). "
                    "Target close rate: > 30%.",
        required_skills=["Negotiation", "Solution Demo"],
        training_data={
            "crm_modules_used": [
                {"module": "opportunities", "usage": "Review negotiation-stage deals. Track decision timeline."},
                {"module": "contacts", "usage": "Identify decision makers, champions, blockers."},
                {"module": "bob_assistant", "usage": "Generate proposals, ROI business cases, objection responses."},
            ],
            "bob_assistance": [
                "Génère un business case ROI personnalisé pour chaque opportunité",
                "Prépare des réponses aux objections courantes",
                "Crée des propositions avec options de pricing",
                "Analyse les patterns des deals perdus pour amélioration",
                "Rappelle automatiquement les follow-ups à 48h",
            ],
            "success_metrics": {
                "close_rate": "> 30%",
                "avg_deal_size": "> $5,000 ARR",
                "negotiation_duration": "< 14 jours en moyenne",
                "proposal_sent_to_close": "< 7 jours",
                "win_loss_analysis": "Post-mortem documenté pour chaque deal perdu",
            },
            "compliance_notes": [
                "Pricing doit respecter la politique tarifaire approuvée",
                "Pas de remises > 20% sans approbation du management",
                "Contrats doivent inclure les termes standards de service",
            ],
            "tools_required": [
                "Croo Digital Experience — Opportunities & Contacts",
                "Bob AI — Business case & proposal generation",
                "Document tool for proposals",
            ],
        },
        tenant_id=tenant_id,
    )
    db.add(task_deal_close)
    db.flush()

    for i, step in enumerate([
        "Review deals in 'Negotiation' stage in Croo pipeline",
        "Prepare tailored proposal with pricing options",
        "Build ROI business case (cost savings vs. investment)",
        "Address final objections with proof points and references",
        "Send proposal and schedule decision call",
        "Follow up within 48h if no response",
        "Update deal stage and log outcome in Croo",
    ], 1):
        db.add(BccTaskStep(task_id=task_deal_close.id, step_number=i, instruction=step))

    db.flush()

    # ── Milestones ────────────────────────────────────────────

    milestones = [
        BccMilestone(
            role_id=role.id,
            name="CRM Certified — Croo Expert",
            stage="onboarding",
            sort_order=1,
            criteria={
                "product_knowledge": "Can demo all Croo modules independently",
                "crm_hygiene": "Pipeline updated daily for 5 consecutive days",
                "bob_usage": "Used Bob AI assistant for 3+ tasks",
            },
            tenant_id=tenant_id,
        ),
        BccMilestone(
            role_id=role.id,
            name="First Pipeline Built",
            stage="foundation",
            sort_order=2,
            criteria={
                "leads_generated": "50+ qualified leads in pipeline",
                "outreach_volume": "200+ touchpoints completed",
                "email_compliance": "100% CASL compliant campaigns",
                "icp_mastery": "Can articulate ICP in 30 seconds",
            },
            tenant_id=tenant_id,
        ),
        BccMilestone(
            role_id=role.id,
            name="First Deal Closed",
            stage="practice",
            sort_order=3,
            criteria={
                "demos_delivered": "10+ tailored demos completed",
                "close_rate": "First signed contract",
                "deal_value": "ARR > $5,000",
                "customer_satisfaction": "Positive onboarding feedback",
            },
            tenant_id=tenant_id,
        ),
        BccMilestone(
            role_id=role.id,
            name="Quota Crusher — Autonomous Rep",
            stage="mastery",
            sort_order=4,
            criteria={
                "quota_attainment": "> 100% quarterly quota",
                "pipeline_coverage": "3x pipeline coverage maintained",
                "expansion_revenue": "1+ upsell or cross-sell closed",
                "mentoring": "Helped onboard 1 new rep",
            },
            tenant_id=tenant_id,
        ),
    ]
    for ms in milestones:
        db.add(ms)

    db.commit()
    logger.info("bcc_seed_completed",
                org="The Croo Group",
                industry="Digital Transformation",
                career="Sales Rep",
                skills=6,
                tasks=5,
                milestones=4,
                resources=len(resources),
                regulations=len(regulations))
