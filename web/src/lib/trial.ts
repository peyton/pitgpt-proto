import type { Assignment, IngestionResult, Observation, Protocol, Trial } from "./types";
import { generateSchedule, generateSeed } from "./randomize";

export function createTrial(
  ingestion: IngestionResult,
  conditionALabel: string,
  conditionBLabel: string,
): Trial {
  const protocol = ingestion.protocol!;
  const seed = generateSeed();
  const schedule = generateSchedule(
    protocol.duration_weeks,
    protocol.block_length_days,
    seed,
  );

  return {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    conditionALabel,
    conditionBLabel,
    protocol,
    ingestion,
    schedule,
    seed,
    observations: [],
    status: "active",
  };
}

export function getTrialDayIndex(trial: Trial): number {
  const start = new Date(trial.createdAt);
  const now = new Date();
  start.setHours(0, 0, 0, 0);
  now.setHours(0, 0, 0, 0);
  return Math.floor((now.getTime() - start.getTime()) / 86400000) + 1;
}

export function getCurrentWeek(trial: Trial): number {
  const dayIndex = getTrialDayIndex(trial);
  return Math.floor((dayIndex - 1) / trial.protocol.block_length_days);
}

export function getCurrentAssignment(trial: Trial): Assignment | undefined {
  const week = getCurrentWeek(trial);
  return trial.schedule.find((a) => a.week === week);
}

export function getConditionLabel(trial: Trial, condition: "A" | "B"): string {
  return condition === "A" ? trial.conditionALabel : trial.conditionBLabel;
}

export function getTotalDays(protocol: Protocol): number {
  return protocol.duration_weeks * 7;
}

export function getTrialProgress(trial: Trial) {
  const totalDays = getTotalDays(trial.protocol);
  const dayIndex = Math.min(getTrialDayIndex(trial), totalDays);
  const daysLogged = trial.observations.filter((o) => o.primary_score !== null).length;
  const adherent = trial.observations.filter((o) => o.adherence === "yes").length;
  const adverseEvents = trial.observations.filter((o) => o.irritation === "yes").length;

  return {
    dayIndex,
    totalDays,
    daysLogged,
    adherenceRate: dayIndex > 0 ? Math.round((adherent / dayIndex) * 100) : 0,
    daysLoggedPct: dayIndex > 0 ? Math.round((daysLogged / dayIndex) * 100) : 0,
    adverseEvents,
  };
}

export function hasCheckedInToday(trial: Trial): boolean {
  const today = new Date().toISOString().slice(0, 10);
  return trial.observations.some((o) => o.date === today);
}

export function isTrialComplete(trial: Trial): boolean {
  return getTrialDayIndex(trial) > getTotalDays(trial.protocol);
}

export function checkAdverseEventStreak(trial: Trial): boolean {
  const sorted = [...trial.observations].sort((a, b) => b.day_index - a.day_index);
  let streak = 0;
  for (const obs of sorted) {
    if (obs.irritation === "yes") {
      streak++;
      if (streak >= 3) return true;
    } else {
      break;
    }
  }
  return false;
}

export function canBackfill(_trial: Trial, dateStr: string): boolean {
  const today = new Date();
  const date = new Date(dateStr);
  today.setHours(0, 0, 0, 0);
  date.setHours(0, 0, 0, 0);
  const diffDays = (today.getTime() - date.getTime()) / 86400000;
  return diffDays <= 2 && diffDays >= 0;
}

export function buildObservation(
  trial: Trial,
  score: number,
  irritation: "yes" | "no",
  adherence: "yes" | "no" | "partial",
  note: string,
): Observation {
  const dayIndex = getTrialDayIndex(trial);
  const today = new Date().toISOString().slice(0, 10);
  const assignment = getCurrentAssignment(trial);

  return {
    day_index: dayIndex,
    date: today,
    condition: assignment?.condition ?? "A",
    primary_score: score,
    irritation,
    adherence,
    note,
    is_backfill: "no",
    backfill_days: null,
  };
}

/** Convert trial protocol to the dict format expected by /analyze */
export function protocolToDict(protocol: Protocol): Record<string, unknown> {
  return {
    planned_days: protocol.duration_weeks * 7,
    block_length_days: protocol.block_length_days,
    duration_weeks: protocol.duration_weeks,
    cadence: protocol.cadence,
    washout: protocol.washout,
    primary_outcome_question: protocol.primary_outcome_question,
  };
}
