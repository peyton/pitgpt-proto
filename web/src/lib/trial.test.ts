import { describe, expect, it } from "vitest";
import { appendObservationIfNew, buildObservationForDate } from "./trial";
import type { Observation, Trial } from "./types";

const baseObservation: Observation = {
  day_index: 1,
  date: "2026-01-01",
  condition: "A",
  primary_score: 7,
  irritation: "no",
  adherence: "yes",
  note: "",
  is_backfill: "no",
  backfill_days: null,
};

const baseTrial: Trial = {
  id: "trial",
  createdAt: "2026-01-01T00:00:00.000Z",
  conditionALabel: "A",
  conditionBLabel: "B",
  protocol: {
    template: "Custom A/B",
    duration_weeks: 2,
    block_length_days: 7,
    cadence: "daily",
    washout: "None",
    primary_outcome_question: "Score",
    screening: "",
    warnings: "",
  },
  ingestion: {
    decision: "generate_protocol",
    safety_tier: "GREEN",
    evidence_quality: "novel",
    evidence_conflict: false,
    protocol: null,
    block_reason: null,
    user_message: "Ready",
  },
  schedule: [
    { period_index: 0, pair_index: 0, condition: "A", start_day: 1, end_day: 7 },
    { period_index: 1, pair_index: 0, condition: "B", start_day: 8, end_day: 14 },
  ],
  seed: 123,
  observations: [baseObservation],
  status: "active",
};

describe("appendObservationIfNew", () => {
  it("ignores duplicate day or date observations", () => {
    const updated = appendObservationIfNew(baseTrial, { ...baseObservation, primary_score: 8 });

    expect(updated).toBe(baseTrial);
    expect(updated.observations).toHaveLength(1);
  });

  it("appends a new observation", () => {
    const updated = appendObservationIfNew(baseTrial, {
      ...baseObservation,
      day_index: 2,
      date: "2026-01-02",
    });

    expect(updated).not.toBe(baseTrial);
    expect(updated.observations).toHaveLength(2);
    expect(updated.events?.some((event) => event.type === "checkin_submitted")).toBe(true);
  });

  it("preserves discomfort as an adverse event", () => {
    const updated = appendObservationIfNew(baseTrial, {
      ...baseObservation,
      day_index: 2,
      date: "2026-01-02",
      irritation: "yes",
      adverse_event_severity: "moderate",
      adverse_event_description: "Redness after use.",
    });

    expect(updated.adverseEvents).toHaveLength(1);
    expect(updated.adverseEvents?.[0]?.description).toBe("Redness after use.");
    expect(updated.events?.some((event) => event.type === "adverse_event_logged")).toBe(true);
  });

  it("builds observations with adherence reasons and secondary scores", () => {
    const observation = buildObservationForDate(
      baseTrial,
      "2026-01-02",
      6,
      "yes",
      "partial",
      "Travel day.",
      {
        adherenceReason: "Skipped the evening step.",
        adverseEventSeverity: "mild",
        adverseEventDescription: "Redness.",
        secondaryScores: { sleep: 4 },
      },
    );

    expect(observation.adherence_reason).toBe("Skipped the evening step.");
    expect(observation.adverse_event_severity).toBe("mild");
    expect(observation.adverse_event_description).toBe("Redness.");
    expect(observation.secondary_scores).toEqual({ sleep: 4 });
  });
});
