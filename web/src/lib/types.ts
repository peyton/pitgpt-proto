// Mirrors pitgpt/core/models.py

export type SafetyTier = "GREEN" | "YELLOW" | "RED";
export type EvidenceQuality = "novel" | "weak" | "moderate" | "strong";
export type QualityGrade = "A" | "B" | "C" | "D";
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
}

export interface Observation {
  day_index: number;
  date: string;
  condition: string;
  primary_score: number | null;
  irritation: string;
  adherence: string;
  note: string;
  is_backfill: string;
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

export interface ResultCard {
  quality_grade: QualityGrade;
  verdict: Verdict;
  mean_a: number | null;
  mean_b: number | null;
  difference: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  cohens_d: number | null;
  n_used_a: number;
  n_used_b: number;
  adherence_rate: number;
  days_logged_pct: number;
  early_stop: boolean;
  late_backfill_excluded: number;
  block_breakdown: BlockBreakdown[];
  sensitivity_excluding_partial: SensitivityResult | null;
  planned_days_defaulted: boolean;
  summary: string;
  caveats: string;
}

// Client-only types

export interface Assignment {
  week: number;
  condition: "A" | "B";
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
  trial: Trial | null;
  completedResults: CompletedTrial[];
  settings: Settings;
}

export interface CompletedTrial {
  trial: Trial;
  result: ResultCard;
}
