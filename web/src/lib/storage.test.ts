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
        adherence_reason: "",
        note: 'sleep, "travel"',
        is_backfill: "no",
        backfill_days: null,
      },
    ]);

    expect(csv).toContain('"sleep, ""travel"""');
    expect(csv.split("\n")[0]).toBe(
      '"observation_id","day_index","date","condition","assigned_condition","actual_condition","primary_score","irritation","adherence","adherence_reason","note","is_backfill","backfill_days","adverse_event_severity","adverse_event_description","secondary_scores","recorded_at","timezone","planned_checkin_time","minutes_from_planned_checkin","exposure_start_at","exposure_end_at","measurement_timing","deviation_codes","confounders","rescue_action"',
    );
    expect(csv).toContain('"{}"');
    expect(csv).toContain('"[]"');
  });

  it("migrates provider settings with reserved on-device runtime disabled", () => {
    const state = restoreStateFromJSON(JSON.stringify({
      trial: null,
      completedResults: [],
      settings: {
        preferredProvider: "ollama",
        preferredModel: "llama3.1:latest",
        localAiConsentByProvider: { ollama: true },
        onDeviceModelRuntimeEnabled: true,
      },
    }));

    expect(state.settings.preferredProvider).toBe("ollama");
    expect(state.settings.preferredModel).toBe("llama3.1:latest");
    expect(state.settings.localAiConsentByProvider.ollama).toBe(true);
    expect(state.settings.onDeviceModelRuntimeEnabled).toBe(false);
  });

  it("drops invalid provider settings and malformed reminder times", () => {
    const state = restoreStateFromJSON(JSON.stringify({
      trial: null,
      completedResults: [],
      settings: {
        preferredProvider: "unknown",
        reminderTime: "99:99",
        localAiConsentByProvider: { unknown: true, ollama: true, openrouter: "yes" },
      },
    }));

    expect(state.settings.preferredProvider).toBe("openrouter");
    expect(state.settings.reminderTime).toBe("21:00");
    expect(state.settings.localAiConsentByProvider).toEqual({ ollama: true });
  });

  it("migrates API token and trial extension fields", () => {
    const state = restoreStateFromJSON(JSON.stringify({
      trial: {
        id: "trial",
        createdAt: "2026-01-01T00:00:00.000Z",
        conditionALabel: "A label",
        conditionBLabel: "B label",
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
        seed: 123,
        schedule: [],
        observations: [{ day_index: 1, date: "2026-01-01", condition: "A" }],
        status: "active",
      },
      completedResults: [],
      settings: { apiToken: "secret" },
    }));

    expect(state.settings.apiToken).toBe("secret");
    expect(state.trial?.protocol.condition_a_label).toBe("A label");
    expect(state.trial?.protocol.secondary_outcomes).toEqual([]);
    expect(state.trial?.protocol.amendments).toEqual([]);
    expect(state.trial?.observations[0]?.secondary_scores).toEqual({});
    expect(state.trial?.observations[0]?.actual_condition).toBe("A");
    expect(state.trial?.observations[0]?.deviation_codes).toEqual([]);
    expect(state.trial?.observations[0]?.confounders).toEqual({});
  });

  it("normalizes without mutating imported objects", () => {
    const raw = {
      trial: {
        id: "trial",
        createdAt: "2026-01-01T00:00:00.000Z",
        conditionALabel: "  A label  ",
        conditionBLabel: "B label",
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
        seed: 123,
        schedule: [],
        observations: [{ day_index: 1, date: "2026-01-01", condition: "A" }],
        status: "active",
      },
      completedResults: [],
      settings: {},
    };

    const state = restoreStateFromJSON(JSON.stringify(raw));

    expect(raw.trial.protocol).not.toHaveProperty("condition_a_label");
    expect(state.trial?.conditionALabel).toBe("A label");
    expect(state.trial?.protocol.condition_a_label).toBe("A label");
  });
});
