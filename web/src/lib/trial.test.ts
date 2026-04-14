import { describe, expect, it } from "vitest";
import {
  appendObservationIfNew,
  buildObservationForDate,
  canBackfill,
  canonicalJson,
  checkAdverseEventStreak,
  createTrial,
  getCurrentPeriodIndex,
  getDaysLeft,
  stableHash,
} from "./trial";
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
    expect(observation.assigned_condition).toBe("A");
    expect(observation.actual_condition).toBe("A");
    expect(observation.observation_id).toMatch(/^obs-/);
    expect(observation.deviation_codes).toEqual([]);
    expect(observation.confounders).toEqual({});
  });
});

describe("createTrial", () => {
  it("does not mutate the ingestion result while locking labels", () => {
    const ingestion = {
      ...baseTrial.ingestion,
      protocol: {
        ...baseTrial.protocol,
        condition_a_label: "Original A",
        condition_b_label: "Original B",
      },
    };

    const trial = createTrial(ingestion, "  Test A  ", "");

    expect(ingestion.protocol?.condition_a_label).toBe("Original A");
    expect(trial.conditionALabel).toBe("Test A");
    expect(trial.conditionBLabel).toBe("Original B");
    expect(trial.ingestion.protocol?.condition_a_label).toBe("Test A");
  });
});

describe("trial date helpers", () => {
  it("does not allow backfills before the trial starts", () => {
    const tomorrowTrial = {
      ...baseTrial,
      createdAt: new Date(Date.now() + 86400000).toISOString(),
      observations: [],
    };
    const today = new Date();
    today.setMinutes(today.getMinutes() - today.getTimezoneOffset());

    expect(canBackfill(tomorrowTrial, today.toISOString().slice(0, 10))).toBe(false);
  });

  it("clamps period and days-left math before day one", () => {
    const tomorrowTrial = {
      ...baseTrial,
      createdAt: new Date(Date.now() + 86400000).toISOString(),
      observations: [],
    };

    expect(getCurrentPeriodIndex(tomorrowTrial)).toBe(0);
    expect(getDaysLeft(tomorrowTrial)).toBe(14);
  });

  it("requires truly consecutive irritation days for the safety streak", () => {
    const trial = {
      ...baseTrial,
      observations: [
        { ...baseObservation, day_index: 1, date: "2026-01-01", irritation: "yes" as const },
        { ...baseObservation, day_index: 3, date: "2026-01-03", irritation: "yes" as const },
        { ...baseObservation, day_index: 5, date: "2026-01-05", irritation: "yes" as const },
      ],
    };

    expect(checkAdverseEventStreak(trial)).toBe(false);
  });
});

describe("stableHash", () => {
  it("uses canonical JSON and SHA-256 integrity hashes", () => {
    expect(canonicalJson({ b: 2, a: 1 })).toBe('{"a":1,"b":2}');
    expect(stableHash({ b: 2, a: 1 })).toBe(stableHash({ a: 1, b: 2 }));
    expect(stableHash("abc")).toBe("6cc43f858fbb763301637b5af970e2a46b46f461f27e5a0f41e009c59b827b25");
  });
});
