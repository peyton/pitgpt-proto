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
export type AdverseEventSeverity = "mild" | "moderate" | "severe";
export type OutcomeRole = "primary" | "secondary" | "exploratory" | "safety";
export type IntercurrentEventStrategy =
  | "treatment_policy"
  | "while_on_treatment"
  | "composite_safety"
  | "exclude_invalid";
export type DenominatorPolicy = "planned_days" | "eligible_days" | "observed_days";
export type ActionabilityClass =
  | "switch"
  | "keep_current"
  | "repeat_with_better_controls"
  | "stop_for_safety"
  | "inconclusive_no_action"
  | "insufficient_data";
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
  condition_a_label?: string;
  condition_b_label?: string;
  condition_a_instructions?: string;
  condition_b_instructions?: string;
  primary_outcome?: OutcomeMeasure | null;
  secondary_outcomes?: OutcomeDefinition[];
  amendments?: ProtocolAmendment[];
  suggested_confounders?: string[];
  clinician_note?: string;
  readiness_checklist?: string[];
}

export interface OutcomeDefinition {
  id: string;
  label: string;
  scale_min: number;
  scale_max: number;
  higher_is_better: boolean;
  description?: string;
}

export interface OutcomeMeasure extends OutcomeDefinition {
  role?: OutcomeRole;
  concept_of_interest?: string;
  context_of_use?: string;
  recall_period?: string;
  scoring_instructions?: string;
  anchor_low?: string;
  anchor_mid?: string;
  anchor_high?: string;
  minimum_meaningful_difference_positive?: number;
  minimum_meaningful_difference_negative?: number;
  reliability_notes?: string;
}

export interface ProtocolAmendment {
  date: string;
  field: string;
  old_value?: string;
  new_value?: string;
  reason: string;
}

export interface IntercurrentEventStrategySpec {
  event: string;
  strategy: IntercurrentEventStrategy;
  rationale?: string;
}

export interface PrimaryEstimand {
  estimand_id?: string;
  treatment_contrast?: string;
  outcome_id?: string;
  summary_measure?: string;
  population_scope?: string;
  intercurrent_event_strategies?: IntercurrentEventStrategySpec[];
}

export interface AnalysisPlan {
  plan_id?: string;
  method_version?: string;
  primary_method?: AnalysisMethod;
  fallback_method?: AnalysisMethod;
  denominator_policy?: DenominatorPolicy;
  estimand?: PrimaryEstimand;
  sensitivity_methods?: string[];
  equivalence_margin_source?: string;
  pre_specified?: boolean;
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
  observation_id?: string;
  day_index: number;
  date: string;
  condition: Condition;
  assigned_condition?: Condition | null;
  actual_condition?: Condition | null;
  primary_score: number | null;
  irritation: YesNo;
  adherence: Adherence;
  adherence_reason?: string;
  note: string;
  is_backfill: YesNo;
  backfill_days: number | null;
  adverse_event_severity?: AdverseEventSeverity;
  adverse_event_description?: string;
  secondary_scores?: Record<string, number>;
  recorded_at?: string;
  timezone?: string;
  planned_checkin_time?: string;
  minutes_from_planned_checkin?: number | null;
  exposure_start_at?: string;
  exposure_end_at?: string;
  measurement_timing?: string;
  deviation_codes?: string[];
  confounders?: Record<string, string>;
  rescue_action?: string;
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
  randomization_p_value?: number | null;
}

export interface SensitivityAnalysisResult extends SensitivityResult {
  name: string;
  method: string;
  summary?: string;
}

export interface SecondaryOutcomeResult {
  outcome_id: string;
  label: string;
  mean_a: number | null;
  mean_b: number | null;
  difference: number | null;
  n_used_a: number;
  n_used_b: number;
  summary: string;
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
  relative_change_pct?: number | null;
  paired_block?: PairedBlockEstimate | null;
  welch_sensitivity?: SensitivityAnalysisResult | null;
  n_used_a: number;
  n_used_b: number;
  adherence_rate: number;
  days_logged_pct: number;
  early_stop: boolean;
  late_backfill_excluded: number;
  adverse_event_count?: number;
  adverse_event_by_severity?: Record<string, number>;
  block_breakdown: BlockBreakdown[];
  sensitivity_excluding_partial: SensitivityResult | null;
  sensitivity_analyses?: SensitivityAnalysisResult[];
  secondary_outcomes?: SecondaryOutcomeResult[];
  protocol_amendment_count?: number;
  planned_days_defaulted: boolean;
  minimum_meaningful_difference?: number;
  meets_minimum_meaningful_effect?: boolean | null;
  equivalence_margin?: number | null;
  supports_no_meaningful_difference?: boolean | null;
  randomization_p_value?: number | null;
  actionability?: ActionabilityClass;
  harm_benefit_summary?: string;
  reliability_warnings?: string[];
  dataset_snapshot?: AnalysisDatasetSnapshot;
  methods_appendix?: MethodsAppendix;
  data_warnings?: string[];
  summary: string;
  caveats: string;
}

export interface TrialLock {
  protocol_hash?: string;
  analysis_plan_hash?: string;
  schedule_hash?: string;
  estimand_hash?: string;
  locked_at?: string;
  hash_algorithm?: "sha256" | string;
}

export interface RowExclusion {
  day_index: number;
  date?: string;
  condition?: Condition | null;
  reason: string;
  safety_retained?: boolean;
}

export interface AnalysisDatasetSnapshot {
  rows_total: number;
  rows_used_primary: number;
  rows_used_safety: number;
  rows_excluded_primary: number;
  exclusions?: RowExclusion[];
  denominator_policy?: DenominatorPolicy;
}

export interface MethodsAppendix {
  method_version?: string;
  estimand?: PrimaryEstimand;
  analysis_plan?: AnalysisPlan;
  trial_lock?: TrialLock;
  input_hashes?: Record<string, string>;
  sensitivity_methods?: string[];
  row_exclusion_reasons?: string[];
  software_versions?: Record<string, string>;
  pre_specified?: boolean;
}

export interface ValidationReport {
  valid: boolean;
  errors: string[];
  warnings: string[];
  observation_count: number;
  planned_days: number | null;
  block_length_days: number | null;
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
  trialLock?: TrialLock;
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
  apiToken: string;
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
