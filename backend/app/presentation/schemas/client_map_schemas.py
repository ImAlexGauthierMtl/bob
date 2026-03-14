"""Pydantic schemas for Client Map 360° — request/response DTOs."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums as string literals ─────────────────────────────────

ROLE_TYPES = ["DECISION_MAKER", "INFLUENCER", "USER", "CHAMPION", "BLOCKER", "GATEKEEPER"]
DISC_PROFILES = ["D", "I", "S", "C", "UNKNOWN"]
COMPANY_CULTURES = ["CONSERVATIVE", "INNOVATIVE", "COST_OBSESSED", "AGILE", "BUREAUCRATIC"]
TRIGGER_TYPES = ["MERGER", "NEW_BUDGET", "CRISIS", "CONTRACT_END", "LEADERSHIP_CHANGE", "COMPETITOR_MOVE", "REGULATION", "OTHER"]
EGO_DRIVERS = ["RECOGNITION", "SECURITY", "TIME", "POWER", "LEGACY"]
EMOTIONAL_CLIMATES = ["DEFENSIVE", "ENTHUSIASTIC", "RUSHED", "TIRED", "NEUTRAL", "CONFIDENT", "FRUSTRATED", "CURIOUS", "HESITANT"]
INTERACTION_TYPES = ["CALL", "MEETING", "EMAIL", "DEMO", "QBR", "SOCIAL"]
NEXT_STEP_OWNERS = ["US", "CLIENT", "BOTH"]


# ── ClientMap Schemas ────────────────────────────────────────

class ClientMapUpsert(BaseModel):
    """Create or update a Client Map (all fields optional for partial upserts)."""

    # Q1: Contexte & Pouvoir
    role_type: Optional[str] = None
    real_role: Optional[str] = None
    disc_profile: Optional[str] = None
    ecosystem_tools: Optional[list[str]] = None
    ecosystem_partners: Optional[list[str]] = None
    company_culture: Optional[str] = None

    # Q2: Douleurs & Déclencheurs
    pain_point: Optional[str] = None
    pain_business_impact: Optional[str] = None
    pain_personal_impact: Optional[str] = None
    inaction_cost: Optional[str] = None
    trigger_event: Optional[str] = None
    trigger_type: Optional[str] = None

    # Q3: WIIFM & Aspirations
    metrics_target: Optional[str] = None
    wiifm_business: Optional[str] = None
    wiifm_personal: Optional[str] = None
    success_vision: Optional[str] = None
    ego_driver: Optional[str] = None

    # Q4: Mécanique & Obstacles
    economic_buyer: Optional[str] = None
    decision_criteria: Optional[str] = None
    decision_process: Optional[str] = None
    paper_process: Optional[str] = None
    champion_name: Optional[str] = None
    competition: Optional[str] = None
    alternative_if_no: Optional[str] = None
    blockers: Optional[str] = None
    timeline_real: Optional[str] = None
    timeline_wished: Optional[str] = None

    # Meta
    trust_level: Optional[int] = Field(None, ge=1, le=5)


class ClientMapResponse(BaseModel):
    """Full Client Map response with computed scores and children."""

    id: str
    contact_id: str

    # Q1
    role_type: Optional[str] = None
    real_role: Optional[str] = None
    disc_profile: Optional[str] = None
    ecosystem_tools: Optional[list[str]] = None
    ecosystem_partners: Optional[list[str]] = None
    company_culture: Optional[str] = None

    # Q2
    pain_point: Optional[str] = None
    pain_business_impact: Optional[str] = None
    pain_personal_impact: Optional[str] = None
    inaction_cost: Optional[str] = None
    trigger_event: Optional[str] = None
    trigger_type: Optional[str] = None

    # Q3
    metrics_target: Optional[str] = None
    wiifm_business: Optional[str] = None
    wiifm_personal: Optional[str] = None
    success_vision: Optional[str] = None
    ego_driver: Optional[str] = None

    # Q4
    economic_buyer: Optional[str] = None
    decision_criteria: Optional[str] = None
    decision_process: Optional[str] = None
    paper_process: Optional[str] = None
    champion_name: Optional[str] = None
    competition: Optional[str] = None
    alternative_if_no: Optional[str] = None
    blockers: Optional[str] = None
    timeline_real: Optional[str] = None
    timeline_wished: Optional[str] = None

    # Meta
    trust_level: int = 1
    meddpicc_score: int = 0
    behavioral_profile: Optional[dict] = None
    last_behavioral_analysis: Optional[datetime] = None

    # Children
    golden_notes: list["GoldenNoteResponse"] = []

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── GoldenNote Schemas ───────────────────────────────────────

class GoldenNoteCreate(BaseModel):
    """Create a new Golden Note."""

    interaction_date: datetime
    interaction_type: str
    verbatim: Optional[str] = None
    silence_observed: Optional[str] = None
    emotional_climate: Optional[str] = None
    next_step: Optional[str] = None
    next_step_owner: Optional[str] = None
    next_step_deadline: Optional[date] = None


class GoldenNoteUpdate(BaseModel):
    """Update an existing Golden Note (all fields optional)."""

    interaction_date: Optional[datetime] = None
    interaction_type: Optional[str] = None
    verbatim: Optional[str] = None
    silence_observed: Optional[str] = None
    emotional_climate: Optional[str] = None
    next_step: Optional[str] = None
    next_step_owner: Optional[str] = None
    next_step_deadline: Optional[date] = None


class GoldenNoteResponse(BaseModel):
    """Golden Note response."""

    id: str
    client_map_id: str
    interaction_date: datetime
    interaction_type: str
    verbatim: Optional[str] = None
    silence_observed: Optional[str] = None
    emotional_climate: Optional[str] = None
    next_step: Optional[str] = None
    next_step_owner: Optional[str] = None
    next_step_deadline: Optional[date] = None
    ai_extracted_insights: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── MEDDPICC Score Detail ────────────────────────────────────

class MeddpiccScoreDetail(BaseModel):
    """Detailed MEDDPICC score breakdown."""

    total_score: int
    max_score: int = 100
    components: dict[str, dict]  # {"M": {"label": "Metrics", "score": 10, "max": 12, "fields": [...]}}
