import type { CompletedTrial, IngestionResult, Observation, Protocol, ResultCard } from "./types";

export interface TrialTemplate {
  id: string;
  icon: string;
  name: string;
  description: string;
  query: string;
  conditionAPlaceholder: string;
  conditionBPlaceholder: string;
  protocol: Protocol;
}

export const trialTemplates: TrialTemplate[] = [
  {
    id: "skincare",
    icon: "AB",
    name: "Skincare A/B",
    description: "Compare two cosmetic products over 6 weeks.",
    query: "Compare two skincare products",
    conditionAPlaceholder: "CeraVe Moisturizing Cream",
    conditionBPlaceholder: "La Roche-Posay Toleriane",
    protocol: {
      template: "Skincare Product",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Skin satisfaction (0-10)",
      screening: "",
      warnings: "",
    },
  },
  {
    id: "morning-routine",
    icon: "AM",
    name: "Morning Routine",
    description: "Compare two morning routines with daily ratings.",
    query: "Compare two morning routines",
    conditionAPlaceholder: "Current morning routine",
    conditionBPlaceholder: "New morning routine",
    protocol: {
      template: "Morning Routine",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Midday appearance (0-10)",
      screening: "",
      warnings: "",
    },
  },
  {
    id: "sleep-routine",
    icon: "SL",
    name: "Sleep Routine",
    description: "Compare two low-risk sleep habit routines.",
    query: "Compare two sleep routines",
    conditionAPlaceholder: "Current sleep routine",
    conditionBPlaceholder: "New sleep routine",
    protocol: {
      template: "Sleep Routine",
      duration_weeks: 4,
      block_length_days: 7,
      cadence: "daily AM",
      washout: "1-2 days",
      primary_outcome_question: "Sleep quality (0-10)",
      screening: "",
      warnings: "Keep timing and environment as consistent as practical.",
    },
  },
  {
    id: "haircare",
    icon: "HR",
    name: "Haircare",
    description: "Compare two haircare products over 6 weeks.",
    query: "Compare two haircare products",
    conditionAPlaceholder: "Current hair product",
    conditionBPlaceholder: "New hair product",
    protocol: {
      template: "Haircare Product",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Hair quality (0-10)",
      screening: "",
      warnings: "",
    },
  },
  {
    id: "evening-routine",
    icon: "PM",
    name: "Evening Routine",
    description: "Compare two evening routines with morning ratings.",
    query: "Compare two evening routines",
    conditionAPlaceholder: "Current evening routine",
    conditionBPlaceholder: "New evening routine",
    protocol: {
      template: "Evening Routine",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Morning skin feel (0-10)",
      screening: "",
      warnings: "",
    },
  },
  {
    id: "custom-ab",
    icon: "C",
    name: "Custom A/B",
    description: "Compare everyday routines or products.",
    query: "Custom A/B experiment",
    conditionAPlaceholder: "Condition A",
    conditionBPlaceholder: "Condition B",
    protocol: {
      template: "Custom A/B",
      duration_weeks: 6,
      block_length_days: 7,
      cadence: "daily",
      washout: "None",
      primary_outcome_question: "Personal outcome rating (0-10)",
      screening: "Use this only for everyday routines or products.",
      warnings:
        "This tool is for comparing everyday routines and products. Do not use it for medications, supplements, or medical-condition experiments.",
    },
  },
];

export function templateToIngestionResult(template: TrialTemplate): IngestionResult {
  return {
    decision: "generate_protocol",
    safety_tier: "GREEN",
    evidence_quality: "novel",
    evidence_conflict: false,
    protocol: template.protocol,
    block_reason: null,
    policy_version: "local-template",
    model: null,
    response_validation_status: "template",
    source_summaries: [],
    claimed_outcomes: [],
    user_message:
      "Template protocol ready. Edit the condition labels, then lock the protocol before collecting data.",
  };
}

export function createExampleCompletedTrial(result: ResultCard): CompletedTrial {
  const protocol: Protocol = {
    template: "Example A/B",
    duration_weeks: 2,
    block_length_days: 7,
    cadence: "daily",
    washout: "None",
    primary_outcome_question: "Comfort rating (0-10)",
    screening: "",
    warnings: "",
  };
  return {
    trial: {
      id: "example-trial",
      createdAt: "2026-01-01T08:00:00.000Z",
      conditionALabel: "Routine A",
      conditionBLabel: "Routine B",
      protocol,
      ingestion: {
        decision: "generate_protocol",
        safety_tier: "GREEN",
        evidence_quality: "moderate",
        evidence_conflict: false,
        protocol,
        block_reason: null,
        policy_version: "example",
        model: null,
        response_validation_status: "example",
        source_summaries: [],
        claimed_outcomes: [],
        user_message: "Example trial loaded from bundled data.",
      },
      seed: 101,
      schedule: [
        { period_index: 0, pair_index: 0, condition: "A", start_day: 1, end_day: 7, week: 0 },
        { period_index: 1, pair_index: 0, condition: "B", start_day: 8, end_day: 14, week: 1 },
      ],
      observations: exampleObservations,
      status: "completed",
      completedAt: "2026-01-14T20:00:00.000Z",
    },
    result,
  };
}

export const exampleObservations: Observation[] = [
  { day_index: 1, date: "2026-01-01", condition: "A", primary_score: 7, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 2, date: "2026-01-02", condition: "A", primary_score: 8, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 3, date: "2026-01-03", condition: "A", primary_score: 7, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 4, date: "2026-01-04", condition: "A", primary_score: 6, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 5, date: "2026-01-05", condition: "A", primary_score: 8, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 6, date: "2026-01-06", condition: "A", primary_score: 7, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 7, date: "2026-01-07", condition: "A", primary_score: 7, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 8, date: "2026-01-08", condition: "B", primary_score: 5, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 9, date: "2026-01-09", condition: "B", primary_score: 6, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 10, date: "2026-01-10", condition: "B", primary_score: 5, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 11, date: "2026-01-11", condition: "B", primary_score: 4, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 12, date: "2026-01-12", condition: "B", primary_score: 6, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 13, date: "2026-01-13", condition: "B", primary_score: 5, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
  { day_index: 14, date: "2026-01-14", condition: "B", primary_score: 5, irritation: "no", adherence: "yes", note: "", is_backfill: "no", backfill_days: null },
];
