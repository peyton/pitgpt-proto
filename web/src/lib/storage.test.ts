import { describe, expect, it } from "vitest";
import { exportCSV, restoreStateFromJSON, STORAGE_VERSION } from "./storage";

describe("storage", () => {
  it("migrates old week schedules to period assignments", () => {
    const state = restoreStateFromJSON(JSON.stringify({
      trial: {
        id: "trial",
        createdAt: "2026-01-01T00:00:00.000Z",
        conditionALabel: "A",
        conditionBLabel: "B",
        protocol: {
          template: "Custom A/B",
          duration_weeks: 6,
          block_length_days: 14,
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
        seed: 123,
        schedule: [{ week: 0, condition: "A" }],
        observations: [],
        status: "active",
      },
      completedResults: [],
      settings: {},
    }));

    expect(state.version).toBe(STORAGE_VERSION);
    expect(state.trial?.schedule).toHaveLength(3);
    expect(state.trial?.schedule.at(0)?.start_day).toBe(1);
    expect(state.trial?.schedule.at(2)?.end_day).toBe(42);
  });

  it("escapes CSV cells consistently", () => {
    const csv = exportCSV([
      {
        day_index: 1,
        date: "2026-01-01",
        condition: "A",
        primary_score: 7,
        irritation: "no",
        adherence: "yes",
        note: 'sleep, "travel"',
        is_backfill: "no",
        backfill_days: null,
      },
    ]);

    expect(csv).toContain('"sleep, ""travel"""');
    expect(csv.split("\n")[0]).toBe(
      '"day_index","date","condition","primary_score","irritation","adherence","note","is_backfill","backfill_days"',
    );
  });
});
