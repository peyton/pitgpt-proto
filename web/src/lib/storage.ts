import { generateSchedule } from "./randomize";
import type { AppState, Observation, Settings, Trial } from "./types";

const STORAGE_KEY = "pitgpt_state";
export const STORAGE_VERSION = 2;

export const defaultSettings: Settings = {
  reminderEnabled: true,
  reminderTime: "21:00",
  emailReminderEnabled: false,
};

export function defaultState(): AppState {
  return { version: STORAGE_VERSION, trial: null, completedResults: [], settings: { ...defaultSettings } };
}

export function loadState(): AppState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return normalizeState(JSON.parse(raw));
  } catch {
    // corrupted state — start fresh
  }
  return defaultState();
}

export function saveState(state: AppState): void {
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
    "note",
    "is_backfill",
    "backfill_days",
  ];
  const rows = observations.map((o) =>
    [
      o.day_index,
      o.date,
      o.condition,
      o.primary_score ?? "",
      o.irritation,
      o.adherence,
      o.note,
      o.is_backfill,
      o.backfill_days ?? "",
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
  };
}

function normalizeTrial(value: unknown): Trial | null {
  if (!isRecord(value) || !isRecord(value.protocol)) return null;
  const trial = value as unknown as Trial;
  if (!Array.isArray(trial.observations)) trial.observations = [];
  if (!Array.isArray(trial.schedule) || needsScheduleMigration(trial)) {
    trial.schedule = generateSchedule(
      trial.protocol.duration_weeks,
      trial.protocol.block_length_days,
      Number.isFinite(trial.seed) ? trial.seed : 0,
    );
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
