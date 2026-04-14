import { generateSchedule } from "./randomize";
import { isTauriRuntime, invokeNative } from "./runtime";
import { stableHash } from "./trial";
import type { AppState, Observation, Settings, Trial } from "./types";

const STORAGE_KEY = "pitgpt_state";
export const STORAGE_VERSION = 3;
const PROVIDER_KINDS = new Set<Settings["preferredProvider"]>([
  "openrouter",
  "ollama",
  "claude_cli",
  "codex_cli",
  "chatgpt_cli",
  "ios_on_device",
]);
const TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;

export const defaultSettings: Settings = {
  reminderEnabled: true,
  reminderTime: "21:00",
  emailReminderEnabled: false,
  apiToken: "",
  preferredProvider: "openrouter",
  preferredModel: "",
  localAiConsentByProvider: {},
  onDeviceModelRuntimeEnabled: false,
};

export function defaultState(): AppState {
  return {
    version: STORAGE_VERSION,
    trial: null,
    completedResults: [],
    settings: { ...defaultSettings },
  };
}

export function loadState(): AppState {
  if (isTauriRuntime()) return defaultState();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return normalizeState(JSON.parse(raw));
  } catch {
    // corrupted state — start fresh
  }
  return defaultState();
}

export async function loadStateAsync(): Promise<AppState> {
  if (!isTauriRuntime()) return loadState();
  try {
    const raw = await invokeNative<unknown | null>("load_app_state");
    if (raw) return normalizeState(raw);
  } catch {
    // Native state is optional; corrupt or missing state starts fresh.
  }
  return defaultState();
}

export function saveState(state: AppState): void {
  if (isTauriRuntime()) {
    void invokeNative("save_app_state", { state: normalizeState(state) });
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeState(state)));
}

export function restoreStateFromJSON(content: string): AppState {
  try {
    return normalizeState(JSON.parse(content));
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : "Import file is not valid JSON.");
  }
}

export function clearAllData(): void {
  if (isTauriRuntime()) {
    void invokeNative("clear_app_state");
    return;
  }
  localStorage.removeItem(STORAGE_KEY);
}

export function exportCSV(observations: Observation[]): string {
  const headers = [
    "observation_id",
    "day_index",
    "date",
    "condition",
    "assigned_condition",
    "actual_condition",
    "primary_score",
    "irritation",
    "adherence",
    "adherence_reason",
    "note",
    "is_backfill",
    "backfill_days",
    "adverse_event_severity",
    "adverse_event_description",
    "secondary_scores",
    "recorded_at",
    "timezone",
    "planned_checkin_time",
    "minutes_from_planned_checkin",
    "exposure_start_at",
    "exposure_end_at",
    "measurement_timing",
    "deviation_codes",
    "confounders",
    "rescue_action",
  ];
  const rows = observations.map((o) =>
    [
      o.observation_id ?? "",
      o.day_index,
      o.date,
      o.condition,
      o.assigned_condition ?? "",
      o.actual_condition ?? "",
      o.primary_score ?? "",
      o.irritation,
      o.adherence,
      o.adherence_reason ?? "",
      o.note,
      o.is_backfill,
      o.backfill_days ?? "",
      o.adverse_event_severity ?? "",
      o.adverse_event_description ?? "",
      JSON.stringify(o.secondary_scores ?? {}),
      o.recorded_at ?? "",
      o.timezone ?? "",
      o.planned_checkin_time ?? "",
      o.minutes_from_planned_checkin ?? "",
      o.exposure_start_at ?? "",
      o.exposure_end_at ?? "",
      o.measurement_timing ?? "",
      JSON.stringify(o.deviation_codes ?? []),
      JSON.stringify(o.confounders ?? {}),
      o.rescue_action ?? "",
    ]
      .map(csvCell)
      .join(","),
  );
  return `${[headers.map(csvCell).join(","), ...rows].join("\n")}\n`;
}

export function exportJSON(state: AppState): string {
  return JSON.stringify(normalizeState(state), null, 2);
}

export function downloadFile(content: string, filename: string, type: string): void {
  if (isTauriRuntime()) {
    void invokeNative("export_file", { filename, content });
    return;
  }
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function csvCell(value: string | number): string {
  const text = String(value);
  return `"${text.replace(/"/g, '""')}"`;
}

function normalizeState(value: unknown): AppState {
  if (!isRecord(value)) return defaultState();
  return {
    version: STORAGE_VERSION,
    trial: normalizeTrial(value.trial),
    completedResults: Array.isArray(value.completedResults)
      ? value.completedResults
          .map((item) =>
            isRecord(item) ? { trial: normalizeTrial(item.trial), result: item.result } : null,
          )
          .filter((item): item is AppState["completedResults"][number] =>
            Boolean(item?.trial && item.result),
          )
      : [],
    settings: normalizeSettings(value.settings),
  };
}

function normalizeSettings(value: unknown): Settings {
  if (!isRecord(value)) return { ...defaultSettings };
  const preferredProvider = isProviderKind(value.preferredProvider)
    ? value.preferredProvider
    : defaultSettings.preferredProvider;
  return {
    reminderEnabled: typeof value.reminderEnabled === "boolean" ? value.reminderEnabled : true,
    reminderTime:
      typeof value.reminderTime === "string" && TIME_PATTERN.test(value.reminderTime)
        ? value.reminderTime
        : "21:00",
    emailReminderEnabled:
      typeof value.emailReminderEnabled === "boolean" ? value.emailReminderEnabled : false,
    apiToken: typeof value.apiToken === "string" ? value.apiToken : "",
    preferredProvider,
    preferredModel: typeof value.preferredModel === "string" ? value.preferredModel : "",
    localAiConsentByProvider: normalizeConsent(value.localAiConsentByProvider),
    onDeviceModelRuntimeEnabled: false,
  };
}

function normalizeTrial(value: unknown): Trial | null {
  if (!isRecord(value) || !isRecord(value.protocol)) return null;
  const input = value as unknown as Trial;
  const conditionALabel = nonEmptyString(input.conditionALabel, "Condition A");
  const conditionBLabel = nonEmptyString(input.conditionBLabel, "Condition B");
  const protocol = {
    ...input.protocol,
    condition_a_label: nonEmptyString(input.protocol.condition_a_label, conditionALabel),
    condition_b_label: nonEmptyString(input.protocol.condition_b_label, conditionBLabel),
    secondary_outcomes: Array.isArray(input.protocol.secondary_outcomes)
      ? input.protocol.secondary_outcomes
      : [],
    amendments: Array.isArray(input.protocol.amendments) ? input.protocol.amendments : [],
  };
  const observations = Array.isArray(input.observations) ? input.observations : [];
  const trial: Trial = {
    ...input,
    conditionALabel,
    conditionBLabel,
    protocol,
    observations: observations.map((observation) => ({
      ...observation,
      assigned_condition: observation.assigned_condition ?? null,
      actual_condition: observation.actual_condition ?? observation.condition,
      secondary_scores: observation.secondary_scores ?? {},
      deviation_codes: observation.deviation_codes ?? [],
      confounders: observation.confounders ?? {},
    })),
    events: Array.isArray(input.events) ? input.events : [],
    adverseEvents: Array.isArray(input.adverseEvents) ? input.adverseEvents : [],
  };
  if (!Array.isArray(trial.schedule) || needsScheduleMigration(trial)) {
    trial.schedule = generateSchedule(
      trial.protocol.duration_weeks,
      trial.protocol.block_length_days,
      Number.isFinite(trial.seed) ? trial.seed : 0,
    );
  }
  if (!trial.protocolHash) {
    trial.protocolHash = stableHash({
      protocol: trial.protocol,
      conditionALabel: trial.conditionALabel,
      conditionBLabel: trial.conditionBLabel,
    });
  }
  if (!trial.analysisPlanHash) {
    trial.analysisPlanHash = stableHash({
      planned_days: trial.protocol.duration_weeks * 7,
      block_length_days: trial.protocol.block_length_days,
      method: "paired_periods_plus_welch_sensitivity",
      minimum_meaningful_difference: 0.5,
    });
  }
  return trial;
}

function needsScheduleMigration(trial: Trial): boolean {
  return trial.schedule.some(
    (assignment) =>
      typeof assignment.period_index !== "number" ||
      typeof assignment.start_day !== "number" ||
      typeof assignment.end_day !== "number",
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isProviderKind(value: unknown): value is Settings["preferredProvider"] {
  return typeof value === "string" && PROVIDER_KINDS.has(value as Settings["preferredProvider"]);
}

function normalizeConsent(value: unknown): Settings["localAiConsentByProvider"] {
  if (!isRecord(value)) return {};
  const consent: Settings["localAiConsentByProvider"] = {};
  for (const [key, enabled] of Object.entries(value)) {
    if (isProviderKind(key) && typeof enabled === "boolean") {
      consent[key] = enabled;
    }
  }
  return consent;
}

function nonEmptyString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}
