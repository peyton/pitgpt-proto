import { describe, expect, it } from "vitest";
import { doctorQuestions, exportAppointmentBrief } from "./brief";
import type { CompletedTrial } from "./types";

const completed: CompletedTrial = {
  trial: {
    id: "trial",
    createdAt: "2026-01-01T00:00:00.000Z",
    conditionALabel: "Morning light",
    conditionBLabel: "Usual routine",
    protocolHash: "abc123",
    analysisPlanHash: "def456",
    protocol: {
      template: "Sleep Routine",
      duration_weeks: 4,
      block_length_days: 7,
      cadence: "daily AM",
      washout: "None",
      primary_outcome_question: "Morning restfulness (0-10)",
      screening: "Do not change medications or replace care.",
      warnings: "Stop if symptoms worsen.",
      clinician_note: "Consider bringing this plan to your clinician if it affects symptoms.",
    },
    ingestion: {
      decision: "generate_protocol_with_restrictions",
      safety_tier: "YELLOW",
      evidence_quality: "weak",
      evidence_conflict: false,
      risk_level: "condition_adjacent_low",
      risk_rationale: "Low-risk routine with condition context.",
      clinician_note: "Consider bringing this plan to your clinician if it affects symptoms.",
      protocol: null,
      block_reason: null,
      user_message: "Ready with restrictions.",
      sources: [
        {
          source_id: "source-1",
          source_type: "article",
          title: "Light timing note",
          locator: "",
          evidence_quality: "weak",
          summary: "Suggests light timing may affect morning restfulness.",
          rationale: "Not a controlled trial.",
        },
      ],
      extracted_claims: [
        {
          intervention: "morning light",
          comparator: "usual routine",
          routine: "sleep",
          outcome: "morning restfulness",
          population: "",
          duration: "",
          timing: "morning",
          effect_size: "",
          source_refs: ["source-1"],
        },
      ],
    },
    schedule: [
      { period_index: 0, pair_index: 0, condition: "A", start_day: 1, end_day: 7 },
      { period_index: 1, pair_index: 0, condition: "B", start_day: 8, end_day: 14 },
    ],
    seed: 123,
    observations: [
      {
        day_index: 1,
        date: "2026-01-01",
        condition: "A",
        primary_score: 6,
        irritation: "yes",
        adherence: "partial",
        adherence_reason: "Travel",
        note: "Poor sleep after a late flight",
        is_backfill: "no",
        backfill_days: null,
        adverse_event_severity: "mild",
        adverse_event_description: "Headache after routine.",
      },
    ],
    adverseEvents: [
      {
        id: "ae-1",
        date: "2026-01-01",
        day_index: 1,
        condition: "A",
        severity: "mild",
        description: "Headache after routine.",
      },
    ],
    events: [],
    status: "completed",
    completedAt: "2026-01-14T00:00:00.000Z",
  },
  result: {
    quality_grade: "C",
    verdict: "inconclusive",
    mean_a: 6,
    mean_b: 5,
    difference: 1,
    ci_lower: -0.5,
    ci_upper: 2.5,
    cohens_d: null,
    n_used_a: 1,
    n_used_b: 1,
    adherence_rate: 0.75,
    days_logged_pct: 0.8,
    early_stop: false,
    late_backfill_excluded: 0,
    block_breakdown: [],
    sensitivity_excluding_partial: null,
    planned_days_defaulted: false,
    summary: "Results are inconclusive.",
    caveats: "Confidence interval spans zero.",
  },
};

describe("appointment brief", () => {
  it("includes protocol, source, adverse-event, uncertainty, and questions", () => {
    const brief = exportAppointmentBrief(completed);

    expect(brief).toContain("# PitGPT Appointment Brief");
    expect(brief).toContain("Protocol hash: abc123");
    expect(brief).toContain("Light timing note");
    expect(brief).toContain("Headache after routine");
    expect(brief).toContain("Confidence interval spans zero");
    expect(brief).toContain("Questions To Bring");
  });

  it("adds condition-adjacent and adverse-event questions", () => {
    const questions = doctorQuestions(completed.trial, completed.result);

    expect(questions.some((question) => question.includes("repeat or extend"))).toBe(true);
    expect(questions.some((question) => question.includes("discomfort events"))).toBe(true);
  });
});
