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
  return getTrialDayIndexForDate(trial, new Date());
}

export function getTrialDayIndexForDate(trial: Trial, date: Date): number {
  const start = new Date(trial.createdAt);
  start.setHours(0, 0, 0, 0);
  const target = new Date(date);
  target.setHours(0, 0, 0, 0);
  return Math.floor((target.getTime() - start.getTime()) / 86400000) + 1;
}

export function getCurrentWeek(trial: Trial): number {
  const dayIndex = getTrialDayIndex(trial);
  return Math.floor((dayIndex - 1) / trial.protocol.block_length_days);
}

export function getCurrentAssignment(trial: Trial): Assignment | undefined {
  const week = getCurrentWeek(trial);
  return trial.schedule.find((a) => a.week === week);
}

export function getAssignmentForDay(trial: Trial, dayIndex: number): Assignment | undefined {
  const week = Math.floor((dayIndex - 1) / trial.protocol.block_length_days);
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
  const date = parseDateInput(dateStr);
  today.setHours(0, 0, 0, 0);
  date.setHours(0, 0, 0, 0);
  const diffDays = (today.getTime() - date.getTime()) / 86400000;
  return diffDays <= 2 && diffDays >= 0;
}

export function getBackfillDays(dateStr: string): number {
  const today = new Date();
  const date = parseDateInput(dateStr);
  today.setHours(0, 0, 0, 0);
  date.setHours(0, 0, 0, 0);
  return Math.round((today.getTime() - date.getTime()) / 86400000);
}

export function buildObservation(
  trial: Trial,
  score: number,
  irritation: "yes" | "no",
  adherence: "yes" | "no" | "partial",
  note: string,
): Observation {
  const today = new Date().toISOString().slice(0, 10);
  return buildObservationForDate(trial, today, score, irritation, adherence, note);
}

export function buildObservationForDate(
  trial: Trial,
  dateStr: string,
  score: number,
  irritation: "yes" | "no",
  adherence: "yes" | "no" | "partial",
  note: string,
): Observation {
  const date = parseDateInput(dateStr);
  const dayIndex = getTrialDayIndexForDate(trial, date);
  const assignment = getAssignmentForDay(trial, dayIndex);
  const backfillDays = getBackfillDays(dateStr);

  return {
    day_index: dayIndex,
    date: dateStr,
    condition: assignment?.condition ?? "A",
    primary_score: score,
    irritation,
    adherence,
    note,
    is_backfill: backfillDays > 0 ? "yes" : "no",
    backfill_days: backfillDays > 0 ? backfillDays : null,
  };
}

function parseDateInput(dateStr: string): Date {
  const [yearText, monthText, dayText] = dateStr.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  if (!year || !month || !day) return new Date(dateStr);
  return new Date(year, month - 1, day);
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
