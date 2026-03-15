"""Client Map 360° entities — MEDDPICC quadrant, Golden Notes, Insight Triples.

The Client Map is a structured intelligence dossier for each CRM contact,
modeled around the MEDDPICC sales methodology with behavioral analysis.
"""

import enum

from sqlalchemy import (
    Column, String, Text, Integer, Float, Date, DateTime,
    Enum as SAEnum, JSON, ForeignKey,
)
from sqlalchemy.orm import relationship

from shared.database import Base, TenantMixin, AuditMixin, SoftDeleteMixin, generate_uuid


# ── Enums ────────────────────────────────────────────────────

class RoleType(str, enum.Enum):
    DECISION_MAKER = "DECISION_MAKER"
    INFLUENCER = "INFLUENCER"
    USER = "USER"
    CHAMPION = "CHAMPION"
    BLOCKER = "BLOCKER"
    GATEKEEPER = "GATEKEEPER"


class DISCProfile(str, enum.Enum):
    D = "D"  # Dominance
    I = "I"  # Influence
    S = "S"  # Steadiness
    C = "C"  # Conscientiousness
    UNKNOWN = "UNKNOWN"


class CompanyCulture(str, enum.Enum):
    CONSERVATIVE = "CONSERVATIVE"
    INNOVATIVE = "INNOVATIVE"
    COST_OBSESSED = "COST_OBSESSED"
    AGILE = "AGILE"
    BUREAUCRATIC = "BUREAUCRATIC"


class TriggerType(str, enum.Enum):
    MERGER = "MERGER"
    NEW_BUDGET = "NEW_BUDGET"
    CRISIS = "CRISIS"
    CONTRACT_END = "CONTRACT_END"
    LEADERSHIP_CHANGE = "LEADERSHIP_CHANGE"
    COMPETITOR_MOVE = "COMPETITOR_MOVE"
    REGULATION = "REGULATION"
    OTHER = "OTHER"


class EgoDriver(str, enum.Enum):
    RECOGNITION = "RECOGNITION"
    SECURITY = "SECURITY"
    TIME = "TIME"
    POWER = "POWER"
    LEGACY = "LEGACY"


class EmotionalClimate(str, enum.Enum):
    DEFENSIVE = "DEFENSIVE"
    ENTHUSIASTIC = "ENTHUSIASTIC"
    RUSHED = "RUSHED"
    TIRED = "TIRED"
    NEUTRAL = "NEUTRAL"
    CONFIDENT = "CONFIDENT"
    FRUSTRATED = "FRUSTRATED"
    CURIOUS = "CURIOUS"
    HESITANT = "HESITANT"


class InteractionType(str, enum.Enum):
    CALL = "CALL"
    MEETING = "MEETING"
    EMAIL = "EMAIL"
    DEMO = "DEMO"
    QBR = "QBR"
    SOCIAL = "SOCIAL"


class NextStepOwner(str, enum.Enum):
    US = "US"
    CLIENT = "CLIENT"
    BOTH = "BOTH"


class InsightPredicate(str, enum.Enum):
    HAS_PAIN = "HAS_PAIN"
    FEARS = "FEARS"
    WANTS = "WANTS"
    BLOCKS = "BLOCKS"
    INFLUENCES = "INFLUENCES"
    USES = "USES"
    COMPETES_WITH = "COMPETES_WITH"
    REPORTS_TO = "REPORTS_TO"
    CHAMPIONS = "CHAMPIONS"


class DepthLevel(str, enum.Enum):
    SURFACE = "SURFACE"
    BUSINESS = "BUSINESS"
    PERSONAL = "PERSONAL"


class InsightSource(str, enum.Enum):
    MANUAL = "MANUAL"
    AI_PARSED = "AI_PARSED"
    BOB_INFERRED = "BOB_INFERRED"


# ── ClientMap Entity ─────────────────────────────────────────

class ClientMap(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Client Map 360° — MEDDPICC quadrant for a contact."""

    __tablename__ = "client_maps"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # FK → Contact (1:1)
    contact_id = Column(
        String(36), ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    # Contact relationship removed — cross-service (CRM API)

    # ── Q1: Contexte & Pouvoir ───────────────────────────────
    role_type = Column(SAEnum(RoleType), nullable=True)
    real_role = Column(String(200), nullable=True)
    disc_profile = Column(SAEnum(DISCProfile), default=DISCProfile.UNKNOWN)
    ecosystem_tools = Column(JSON, nullable=True, default=list, comment="e.g. ['Salesforce', 'Excel']")
    ecosystem_partners = Column(JSON, nullable=True, default=list, comment="Partners and competitors")
    company_culture = Column(SAEnum(CompanyCulture), nullable=True)

    # ── Q2: Douleurs & Déclencheurs ──────────────────────────
    pain_point = Column(Text, nullable=True, comment="Le 'mal de dent' — surface pain")
    pain_business_impact = Column(Text, nullable=True, comment="Level 2 — business consequence")
    pain_personal_impact = Column(Text, nullable=True, comment="Level 3 — personal/emotional impact")
    inaction_cost = Column(Text, nullable=True, comment="What happens in 6 months if nothing changes")
    trigger_event = Column(Text, nullable=True, comment="Why are they talking to us NOW")
    trigger_type = Column(SAEnum(TriggerType), nullable=True)

    # ── Q3: WIIFM & Aspirations ──────────────────────────────
    metrics_target = Column(Text, nullable=True, comment="M of MEDDPICC — targeted quantified gain")
    wiifm_business = Column(Text, nullable=True, comment="ROI, productivity, market share")
    wiifm_personal = Column(Text, nullable=True, comment="Promotion, stress, work-life — the trust field")
    success_vision = Column(Text, nullable=True, comment="Perfect win in 1 year")
    ego_driver = Column(SAEnum(EgoDriver), nullable=True, comment="What makes them shine to their boss")

    # ── Q4: Mécanique & Obstacles ────────────────────────────
    economic_buyer = Column(Text, nullable=True, comment="E of MEDDPICC — who signs the check")
    decision_criteria = Column(Text, nullable=True, comment="D — technical/financial criteria")
    decision_process = Column(Text, nullable=True, comment="D — internal validation steps")
    paper_process = Column(Text, nullable=True, comment="P — legal/procurement workflow")
    champion_name = Column(Text, nullable=True, comment="C — internal ally")
    competition = Column(Text, nullable=True, comment="C — who else is being evaluated")
    alternative_if_no = Column(Text, nullable=True, comment="What do they do if they don't sign")
    blockers = Column(Text, nullable=True, comment="Fear of change, unallocated budget, politics")
    timeline_real = Column(Text, nullable=True, comment="Real deadlines")
    timeline_wished = Column(Text, nullable=True, comment="Wished deadlines")

    # ── Meta ─────────────────────────────────────────────────
    trust_level = Column(Integer, default=1, comment="1-5 trust indicator")
    meddpicc_score = Column(Integer, default=0, comment="0-100 MEDDPICC completeness")
    behavioral_profile = Column(JSON, nullable=True, comment="AI-computed behavioral analysis")
    last_behavioral_analysis = Column(DateTime(timezone=True), nullable=True)

    # ── Child relations ──────────────────────────────────────
    golden_notes = relationship(
        "GoldenNote", back_populates="client_map",
        cascade="all, delete-orphan", order_by="desc(GoldenNote.interaction_date)",
    )
    insight_triples = relationship(
        "InsightTriple", back_populates="client_map",
        cascade="all, delete-orphan",
    )


# ── GoldenNote Entity ────────────────────────────────────────

class GoldenNote(Base, TenantMixin, AuditMixin, SoftDeleteMixin):
    """Golden Note — post-interaction intelligence entry."""

    __tablename__ = "golden_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # FK → ClientMap
    client_map_id = Column(
        String(36), ForeignKey("client_maps.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    client_map = relationship("ClientMap", back_populates="golden_notes")

    # Interaction context
    interaction_date = Column(DateTime(timezone=True), nullable=False)
    interaction_type = Column(SAEnum(InteractionType), nullable=False)

    # The 3 golden elements
    verbatim = Column(Text, nullable=True, comment="Exact client quote — persuasion weapon")
    silence_observed = Column(Text, nullable=True, comment="What was NOT said but felt")
    emotional_climate = Column(SAEnum(EmotionalClimate), nullable=True)

    # Next step tracking
    next_step = Column(Text, nullable=True, comment="Concrete action the client agreed to")
    next_step_owner = Column(SAEnum(NextStepOwner), nullable=True)
    next_step_deadline = Column(Date, nullable=True)

    # AI enrichment (Phase 2)
    ai_extracted_insights = Column(JSON, nullable=True, comment="Auto-parsed triples by Bob")


# ── InsightTriple Entity ─────────────────────────────────────

class InsightTriple(Base, TenantMixin, AuditMixin):
    """Knowledge Graph triple — Subject → Predicate → Object with depth."""

    __tablename__ = "insight_triples"

    id = Column(String(36), primary_key=True, default=generate_uuid)

    # FK → ClientMap
    client_map_id = Column(
        String(36), ForeignKey("client_maps.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    client_map = relationship("ClientMap", back_populates="insight_triples")

    # Triple structure
    subject_type = Column(String(50), nullable=False, comment="CONTACT, ORGANIZATION, OPPORTUNITY")
    subject_id = Column(String(36), nullable=False)
    predicate = Column(SAEnum(InsightPredicate), nullable=False)
    object_value = Column(Text, nullable=False)
    object_entity_id = Column(String(36), nullable=True, comment="If target is a CRM entity")

    # Depth & confidence
    depth_level = Column(SAEnum(DepthLevel), default=DepthLevel.SURFACE)
    confidence = Column(Float, default=0.5, comment="0-1 confidence score")

    # Source tracking
    source = Column(SAEnum(InsightSource), default=InsightSource.MANUAL)
    source_note_id = Column(
        String(36), ForeignKey("golden_notes.id", ondelete="SET NULL"),
        nullable=True,
    )
