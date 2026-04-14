// Mirrors pitgpt/core/models.py

export type SafetyTier = "GREEN" | "YELLOW" | "RED";
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

export interface Protocol {
  template: string | null;
  duration_weeks: number;
  block_length_days: number;
  cadence: string;
  washout: string;
  primary_outcome_question: string;
  screening: string;
  warnings: string;
}

export interface IngestionResult {
  decision: IngestionDecision;
  safety_tier: SafetyTier;
  evidence_quality: EvidenceQuality;
  evidence_conflict: boolean;
  protocol: Protocol | null;
  block_reason: string | null;
  user_message: string;
  policy_version?: string;
  model?: string | null;
  response_validation_status?: string;
  source_summaries?: string[];
  claimed_outcomes?: string[];
}

export interface Observation {
  day_index: number;
  date: string;
  condition: Condition;
  primary_score: number | null;
  irritation: YesNo;
  adherence: Adherence;
  note: string;
  is_backfill: YesNo;
  backfill_days: number | null;
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
  observations: Observation[];
  status: "active" | "completed" | "stopped";
  completedAt?: string;
}

export interface Settings {
  reminderEnabled: boolean;
  reminderTime: string;
  emailReminderEnabled: boolean;
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
