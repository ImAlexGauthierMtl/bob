/** Client Map 360° — TypeScript interfaces for frontend */

// ── Enums ────────────────────────────────────────────────────

export type RoleType = 'DECISION_MAKER' | 'INFLUENCER' | 'USER' | 'CHAMPION' | 'BLOCKER' | 'GATEKEEPER';
export type DISCProfile = 'D' | 'I' | 'S' | 'C' | 'UNKNOWN';
export type CompanyCulture = 'CONSERVATIVE' | 'INNOVATIVE' | 'COST_OBSESSED' | 'AGILE' | 'BUREAUCRATIC';
export type TriggerType = 'MERGER' | 'NEW_BUDGET' | 'CRISIS' | 'CONTRACT_END' | 'LEADERSHIP_CHANGE' | 'COMPETITOR_MOVE' | 'REGULATION' | 'OTHER';
export type EgoDriver = 'RECOGNITION' | 'SECURITY' | 'TIME' | 'POWER' | 'LEGACY';
export type EmotionalClimate = 'DEFENSIVE' | 'ENTHUSIASTIC' | 'RUSHED' | 'TIRED' | 'NEUTRAL' | 'CONFIDENT' | 'FRUSTRATED' | 'CURIOUS' | 'HESITANT';
export type InteractionType = 'CALL' | 'MEETING' | 'EMAIL' | 'DEMO' | 'QBR' | 'SOCIAL';
export type NextStepOwner = 'US' | 'CLIENT' | 'BOTH';

// ── Client Map ──────────────────────────────────────────────

export interface ClientMap {
  id: string;
  contact_id: string;

  // Q1: Contexte & Pouvoir
  role_type?: RoleType;
  real_role?: string;
  disc_profile?: DISCProfile;
  ecosystem_tools?: string[];
  ecosystem_partners?: string[];
  company_culture?: CompanyCulture;

  // Q2: Douleurs & Déclencheurs
  pain_point?: string;
  pain_business_impact?: string;
  pain_personal_impact?: string;
  inaction_cost?: string;
  trigger_event?: string;
  trigger_type?: TriggerType;

  // Q3: WIIFM & Aspirations
  metrics_target?: string;
  wiifm_business?: string;
  wiifm_personal?: string;
  success_vision?: string;
  ego_driver?: EgoDriver;

  // Q4: Mécanique & Obstacles
  economic_buyer?: string;
  decision_criteria?: string;
  decision_process?: string;
  paper_process?: string;
  champion_name?: string;
  competition?: string;
  alternative_if_no?: string;
  blockers?: string;
  timeline_real?: string;
  timeline_wished?: string;

  // Meta
  trust_level: number;
  meddpicc_score: number;
  behavioral_profile?: BehavioralProfile;
  last_behavioral_analysis?: string;

  // Children
  golden_notes: GoldenNote[];
  created_at?: string;
  updated_at?: string;
}

// ── Golden Note ─────────────────────────────────────────────

export interface GoldenNote {
  id: string;
  client_map_id: string;
  interaction_date: string;
  interaction_type: InteractionType;
  verbatim?: string;
  silence_observed?: string;
  emotional_climate?: EmotionalClimate;
  next_step?: string;
  next_step_owner?: NextStepOwner;
  next_step_deadline?: string;
  ai_extracted_insights?: any;
  created_at?: string;
}

export interface CreateGoldenNote {
  interaction_date: string;
  interaction_type: InteractionType;
  verbatim?: string;
  silence_observed?: string;
  emotional_climate?: EmotionalClimate;
  next_step?: string;
  next_step_owner?: NextStepOwner;
  next_step_deadline?: string;
}

// ── Behavioral Profile ──────────────────────────────────────

export interface BehavioralProfile {
  disc_primary: string;
  disc_secondary?: string;
  disc_confidence: number;
  disc_reasoning: string;
  decision_speed: string;
  formality_level: string;
  risk_tolerance: string;
  preferred_channel: string;
  preferred_schedule?: { days: string[]; time: string };
  emotional_baseline: string;
  emotional_trend: string;
  engagement_momentum?: string;
  persuasion_keys?: string[];
  communication_tips?: string[];
}

// ── MEDDPICC Score ──────────────────────────────────────────

export interface MeddpiccScoreDetail {
  total_score: number;
  max_score: number;
  components: Record<string, { label: string; score: number; max: number; filled_fields: number; total_fields: number }>;
}

// ── Enum display helpers ────────────────────────────────────

export const EMOTIONAL_CLIMATE_ICONS: Record<string, string> = {
  DEFENSIVE: '🛡️',
  ENTHUSIASTIC: '🟢',
  RUSHED: '⚡',
  TIRED: '😴',
  NEUTRAL: '😐',
  CONFIDENT: '💪',
  FRUSTRATED: '🔴',
  CURIOUS: '🔍',
  HESITANT: '🟡',
};

export const DISC_LABELS: Record<string, string> = {
  D: 'Dominant',
  I: 'Influent',
  S: 'Stable',
  C: 'Conforme',
  UNKNOWN: 'Non évalué',
};
