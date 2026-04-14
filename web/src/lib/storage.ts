import { generateSchedule } from "./randomize";
import { isTauriRuntime, invokeNative } from "./runtime";
import { stableHash } from "./trial";
import type { AppState, Observation, Settings, Trial } from "./types";

const STORAGE_KEY = "pitgpt_state";
export const STORAGE_VERSION = 2;

export const defaultSettings: Settings = {
  reminderEnabled: true,
  reminderTime: "21:00",
  emailReminderEnabled: false,
  preferredProvider: "openrouter",
  preferredModel: "",
  localAiConsentByProvider: {},
  onDeviceModelRuntimeEnabled: false,
};

export function defaultState(): AppState {
  return { version: STORAGE_VERSION, trial: null, completedResults: [], settings: { ...defaultSettings } };
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
    "day_index",
    "date",
    "condition",
    "primary_score",
    "irritation",
    "adherence",
    "adherence_reason",
    "note",
    "is_backfill",
    "backfill_days",
    "adverse_event_severity",
    "adverse_event_description",
  ];
  const rows = observations.map((o) =>
    [
      o.day_index,
      o.date,
      o.condition,
      o.primary_score ?? "",
      o.irritation,
      o.adherence,
      o.adherence_reason ?? "",
      o.note,
      o.is_backfill,
      o.backfill_days ?? "",
      o.adverse_event_severity ?? "",
      o.adverse_event_description ?? "",
    ]
      .map(csvCell)
      .join(","),
  );
  return [headers.map(csvCell).join(","), ...rows].join("\n");
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
  a.click();
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
          .map((item) => (isRecord(item) ? { trial: normalizeTrial(item.trial), result: item.result } : null))
          .filter((item): item is AppState["completedResults"][number] => Boolean(item?.trial && item.result))
      : [],
    settings: normalizeSettings(value.settings),
  };
}

function normalizeSettings(value: unknown): Settings {
  if (!isRecord(value)) return { ...defaultSettings };
  return {
    reminderEnabled: typeof value.reminderEnabled === "boolean" ? value.reminderEnabled : true,
    reminderTime: typeof value.reminderTime === "string" ? value.reminderTime : "21:00",
    emailReminderEnabled:
      typeof value.emailReminderEnabled === "boolean" ? value.emailReminderEnabled : false,
    preferredProvider:
      typeof value.preferredProvider === "string"
        ? (value.preferredProvider as Settings["preferredProvider"])
        : "openrouter",
    preferredModel: typeof value.preferredModel === "string" ? value.preferredModel : "",
    localAiConsentByProvider: isRecord(value.localAiConsentByProvider)
      ? value.localAiConsentByProvider
      : {},
    onDeviceModelRuntimeEnabled: false,
  };
}

function normalizeTrial(value: unknown): Trial | null {
  if (!isRecord(value) || !isRecord(value.protocol)) return null;
  const trial = value as unknown as Trial;
  if (!Array.isArray(trial.observations)) trial.observations = [];
  if (!Array.isArray(trial.events)) trial.events = [];
  if (!Array.isArray(trial.adverseEvents)) trial.adverseEvents = [];
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
