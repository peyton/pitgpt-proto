import type { CompletedTrial, IngestionResult, Observation, Protocol, ResultCard } from "./types";
import { stableHash } from "./trial";
import sharedTemplates from "../../../shared/trial_templates.json";

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

interface SharedTemplate {
  id: string;
  icon: string;
  name: string;
  description: string;
  query: string;
  condition_a_placeholder: string;
  condition_b_placeholder: string;
  protocol: Protocol;
}

export const trialTemplates: TrialTemplate[] = (sharedTemplates as SharedTemplate[]).map((template) => ({
  id: template.id,
  icon: template.icon,
  name: template.name,
  description: template.description,
  query: template.query,
  conditionAPlaceholder: template.condition_a_placeholder,
  conditionBPlaceholder: template.condition_b_placeholder,
  protocol: template.protocol,
}));

export function templateToIngestionResult(template: TrialTemplate): IngestionResult {
  return {
    decision: "generate_protocol",
    safety_tier: "GREEN",
    evidence_quality: "novel",
    evidence_conflict: false,
    risk_level: "low",
    risk_rationale: "Low-risk routine template.",
    clinician_note: "",
    protocol: template.protocol,
    block_reason: null,
    policy_version: "local-template",
    model: null,
    response_validation_status: "template",
    source_summaries: [],
    claimed_outcomes: [],
    sources: [],
    extracted_claims: [],
    suitability_scores: [
      { dimension: "risk", score: 5, rationale: "Template is limited to reversible routines." },
      { dimension: "reversibility", score: 5, rationale: "The routine can be stopped." },
      { dimension: "urgency", score: 5, rationale: "Not intended for urgent symptoms." },
      { dimension: "medication_interaction", score: 5, rationale: "No medication changes." },
      { dimension: "measurability", score: 4, rationale: "Uses a daily 0-10 rating." },
      { dimension: "burden", score: 4, rationale: "Designed for short daily check-ins." },
    ],
    next_steps: ["Edit condition labels, check the routine instructions, then lock the protocol."],
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
        risk_level: "low",
        risk_rationale: "Bundled example uses a low-risk routine comparison.",
        clinician_note: "",
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
      protocolHash: stableHash({ protocol, conditionALabel: "Routine A", conditionBLabel: "Routine B" }),
      analysisPlanHash: stableHash({
        planned_days: protocol.duration_weeks * 7,
        block_length_days: protocol.block_length_days,
        method: "paired_periods_plus_welch_sensitivity",
        minimum_meaningful_difference: 0.5,
      }),
      events: [
        {
          id: "evt-example-lock",
          type: "protocol_locked",
          timestamp: "2026-01-01T08:00:00.000Z",
          detail: "Locked bundled example protocol.",
        },
        {
          id: "evt-example-analyzed",
          type: "trial_analyzed",
          timestamp: "2026-01-14T20:00:00.000Z",
          detail: "Analyzed bundled example trial.",
        },
      ],
      adverseEvents: [],
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
