// Mirrors pitgpt/core/models.py

export type SafetyTier = "GREEN" | "YELLOW" | "RED";
export type RiskLevel =
  | "low"
  | "condition_adjacent_low"
  | "moderate"
  | "high"
  | "clinician_review";
export type EvidenceQuality = "novel" | "weak" | "moderate" | "strong";
export type QualityGrade = "A" | "B" | "C" | "D";
export type Condition = "A" | "B";
export type YesNo = "yes" | "no";
export type Adherence = "yes" | "no" | "partial";
export type AnalysisMethod = "welch" | "paired_blocks" | "insufficient_data";
export type IngestionDecision =
  | "generate_protocol"
  | "generate_protocol_with_restrictions"
  | "manual_review_before_protocol"
  | "block";
export type Verdict = "favors_a" | "favors_b" | "inconclusive" | "insufficient_data";
export type AiProviderKind =
  | "openrouter"
  | "ollama"
  | "claude_cli"
  | "codex_cli"
  | "chatgpt_cli"
  | "ios_on_device";
export type AiToolStatus =
  | "available"
  | "installed_unavailable"
  | "not_found"
  | "unsupported_platform"
  | "reserved";

export interface Protocol {
  template: string | null;
  duration_weeks: number;
  block_length_days: number;
  cadence: string;
  washout: string;
  primary_outcome_question: string;
  screening: string;
  warnings: string;
  outcome_anchor_low?: string;
  outcome_anchor_mid?: string;
  outcome_anchor_high?: string;
  condition_a_instructions?: string;
  condition_b_instructions?: string;
  suggested_confounders?: string[];
  clinician_note?: string;
  readiness_checklist?: string[];
}

export interface ResearchSource {
  source_id: string;
  source_type: string;
  title: string;
  locator: string;
  evidence_quality: EvidenceQuality | null;
  summary: string;
  rationale: string;
}

export interface ExtractedClaim {
  intervention: string;
  comparator: string;
  routine: string;
  outcome: string;
  population: string;
  duration: string;
  timing: string;
  effect_size: string;
  source_refs: string[];
}

export interface SuitabilityScore {
  dimension: string;
  score: number;
  rationale: string;
}

export interface IngestionResult {
  decision: IngestionDecision;
  safety_tier: SafetyTier;
  evidence_quality: EvidenceQuality;
  evidence_conflict: boolean;
  risk_level?: RiskLevel;
  risk_rationale?: string;
  clinician_note?: string;
  protocol: Protocol | null;
  block_reason: string | null;
  user_message: string;
  policy_version?: string;
  model?: string | null;
  response_validation_status?: string;
  source_summaries?: string[];
  claimed_outcomes?: string[];
  sources?: ResearchSource[];
  extracted_claims?: ExtractedClaim[];
  suitability_scores?: SuitabilityScore[];
  next_steps?: string[];
}

export interface Observation {
  day_index: number;
  date: string;
  condition: Condition;
  primary_score: number | null;
  irritation: YesNo;
  adherence: Adherence;
  adherence_reason?: string;
  note: string;
  is_backfill: YesNo;
  backfill_days: number | null;
  adverse_event_severity?: "mild" | "moderate" | "severe";
  adverse_event_description?: string;
}

export interface BlockBreakdown {
  block_index: number;
  condition: string;
  mean: number;
  n: number;
}

export interface SensitivityResult {
  difference: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  n_used_a: number;
  n_used_b: number;
}

export interface PairedBlockEstimate {
  difference: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  n_pairs: number;
}

export interface ResultCard {
  quality_grade: QualityGrade;
  verdict: Verdict;
  analysis_method?: AnalysisMethod;
  mean_a: number | null;
  mean_b: number | null;
  difference: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  cohens_d: number | null;
  paired_block?: PairedBlockEstimate | null;
  n_used_a: number;
  n_used_b: number;
  adherence_rate: number;
  days_logged_pct: number;
  early_stop: boolean;
  late_backfill_excluded: number;
  block_breakdown: BlockBreakdown[];
  sensitivity_excluding_partial: SensitivityResult | null;
  planned_days_defaulted: boolean;
  minimum_meaningful_difference?: number;
  meets_minimum_meaningful_effect?: boolean | null;
  data_warnings?: string[];
  summary: string;
  caveats: string;
}

// Client-only types

export interface Assignment {
  period_index: number;
  pair_index: number;
  condition: Condition;
  start_day: number;
  end_day: number;
  week?: number;
}

export interface Trial {
  id: string;
  createdAt: string;
  conditionALabel: string;
  conditionBLabel: string;
  protocol: Protocol;
  ingestion: IngestionResult;
  schedule: Assignment[];
  seed: number;
  protocolHash?: string;
  analysisPlanHash?: string;
  events?: TrialEvent[];
  adverseEvents?: AdverseEvent[];
  observations: Observation[];
  status: "active" | "completed" | "stopped";
  completedAt?: string;
}

export interface TrialEvent {
  id: string;
  type:
    | "source_added"
    | "protocol_locked"
    | "checkin_submitted"
    | "backfill_submitted"
    | "adverse_event_logged"
    | "trial_stopped"
    | "trial_analyzed";
  timestamp: string;
  detail: string;
}

export interface AdverseEvent {
  id: string;
  date: string;
  day_index: number;
  condition: Condition;
  severity: "mild" | "moderate" | "severe";
  description: string;
}

export interface Settings {
  reminderEnabled: boolean;
  reminderTime: string;
  emailReminderEnabled: boolean;
  preferredProvider: AiProviderKind;
  preferredModel: string;
  localAiConsentByProvider: Partial<Record<AiProviderKind, boolean>>;
  onDeviceModelRuntimeEnabled: false;
}

export interface AppState {
  version: number;
  trial: Trial | null;
  completedResults: CompletedTrial[];
  settings: Settings;
}

export interface CompletedTrial {
  trial: Trial;
  result: ResultCard;
}

export interface AiProviderInfo {
  kind: AiProviderKind;
  label: string;
  status: AiToolStatus;
  is_local: boolean;
  is_offline: boolean;
  models: string[];
  detail: string;
}
