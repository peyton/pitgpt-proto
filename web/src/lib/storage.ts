import type { AppState, Observation, Settings } from "./types";

const STORAGE_KEY = "pitgpt_state";

const defaultSettings: Settings = {
  reminderEnabled: true,
  reminderTime: "21:00",
  emailReminderEnabled: false,
};

export function loadState(): AppState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as AppState;
  } catch {
    // corrupted state — start fresh
  }
  return { trial: null, completedResults: [], settings: { ...defaultSettings } };
}

export function saveState(state: AppState): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
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
      `"${o.note.replace(/"/g, '""')}"`,
      o.is_backfill,
      o.backfill_days ?? "",
    ].join(","),
  );
  return [headers.join(","), ...rows].join("\n");
}

export function exportJSON(state: AppState): string {
  return JSON.stringify(state, null, 2);
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
