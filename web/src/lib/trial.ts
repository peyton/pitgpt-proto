import type { AdverseEvent, Assignment, IngestionResult, Observation, Protocol, Trial, TrialEvent } from "./types";
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
  const protocolHash = stableHash({ protocol, conditionALabel, conditionBLabel });
  const analysisPlanHash = stableHash({
    planned_days: protocol.duration_weeks * 7,
    block_length_days: protocol.block_length_days,
    method: "paired_periods_plus_welch_sensitivity",
    minimum_meaningful_difference: 0.5,
  });

  return {
    id: crypto.randomUUID(),
    createdAt: new Date().toISOString(),
    conditionALabel,
    conditionBLabel,
    protocol,
    ingestion,
    schedule,
    seed,
    protocolHash,
    analysisPlanHash,
    events: [
      event("protocol_locked", `Locked ${protocol.template ?? "custom"} protocol.`),
      ...sourceEvents(ingestion),
    ],
    adverseEvents: [],
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
  return getCurrentPeriodIndex(trial);
}

export function getCurrentPeriodIndex(trial: Trial): number {
  const dayIndex = getTrialDayIndex(trial);
  return Math.floor((dayIndex - 1) / trial.protocol.block_length_days);
}

export function getCurrentAssignment(trial: Trial): Assignment | undefined {
  const periodIndex = getCurrentPeriodIndex(trial);
  return trial.schedule.find((a) => a.period_index === periodIndex || a.week === periodIndex);
}

export function getAssignmentForDay(trial: Trial, dayIndex: number): Assignment | undefined {
  return trial.schedule.find(
    (a) =>
      (dayIndex >= a.start_day && dayIndex <= a.end_day) ||
      a.week === Math.floor((dayIndex - 1) / trial.protocol.block_length_days),
  );
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
  const today = toLocalDateInput(new Date());
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
  options: {
    adherenceReason?: string;
    adverseEventSeverity?: "mild" | "moderate" | "severe";
    adverseEventDescription?: string;
  } = {},
): Observation {
  const today = toLocalDateInput(new Date());
  return buildObservationForDate(trial, today, score, irritation, adherence, note, options);
}

export function buildObservationForDate(
  trial: Trial,
  dateStr: string,
  score: number,
  irritation: "yes" | "no",
  adherence: "yes" | "no" | "partial",
  note: string,
  options: {
    adherenceReason?: string;
    adverseEventSeverity?: "mild" | "moderate" | "severe";
    adverseEventDescription?: string;
  } = {},
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
    adherence_reason: options.adherenceReason?.trim() || undefined,
    note,
    is_backfill: backfillDays > 0 ? "yes" : "no",
    backfill_days: backfillDays > 0 ? backfillDays : null,
    adverse_event_severity: irritation === "yes" ? (options.adverseEventSeverity ?? "mild") : undefined,
    adverse_event_description:
      irritation === "yes" ? (options.adverseEventDescription?.trim() || note || "Logged during check-in.") : undefined,
  };
}

export function appendObservationIfNew(trial: Trial, observation: Observation): Trial {
  const duplicate = trial.observations.some(
    (item) => item.day_index === observation.day_index || item.date === observation.date,
  );
  if (duplicate) return trial;
  const nextEvents = [
    ...(trial.events ?? []),
    event(
      observation.is_backfill === "yes" ? "backfill_submitted" : "checkin_submitted",
      `Logged day ${observation.day_index} for Condition ${observation.condition}.`,
    ),
  ];
  const adverseEvent = observationToAdverseEvent(observation);
  if (adverseEvent) {
    nextEvents.push(
      event(
        "adverse_event_logged",
        `Logged ${adverseEvent.severity} adverse event on day ${adverseEvent.day_index}.`,
      ),
    );
  }
  return {
    ...trial,
    observations: [...trial.observations, observation],
    adverseEvents: adverseEvent ? [...(trial.adverseEvents ?? []), adverseEvent] : (trial.adverseEvents ?? []),
    events: nextEvents,
  };
}

export function addTrialEvent(trial: Trial, type: TrialEvent["type"], detail: string): Trial {
  return { ...trial, events: [...(trial.events ?? []), event(type, detail)] };
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
    minimum_meaningful_difference: 0.5,
    duration_weeks: protocol.duration_weeks,
    cadence: protocol.cadence,
    washout: protocol.washout,
    primary_outcome_question: protocol.primary_outcome_question,
  };
}

export function getDaysLeft(trial: Trial): number {
  return Math.max(0, getTotalDays(trial.protocol) - getTrialDayIndex(trial) + 1);
}

export function getNextCheckInCopy(trial: Trial): string {
  if (hasCheckedInToday(trial)) return "Next check-in: tomorrow";
  return "Next check-in: today";
}

export function computeTrialAuditHash(trial: Trial): string {
  const payload = JSON.stringify({
    protocol: trial.protocol,
    schedule: trial.schedule,
    seed: trial.seed,
    conditionALabel: trial.conditionALabel,
    conditionBLabel: trial.conditionBLabel,
    protocolHash: trial.protocolHash,
    analysisPlanHash: trial.analysisPlanHash,
  });
  return stableHash(payload);
}

function sourceEvents(ingestion: IngestionResult): TrialEvent[] {
  const sources = ingestion.sources ?? [];
  return sources.map((source) =>
    event("source_added", `Attached ${source.title || source.source_id || "source"}.`),
  );
}

function observationToAdverseEvent(observation: Observation): AdverseEvent | null {
  if (observation.irritation !== "yes") return null;
  return {
    id: id("ae"),
    date: observation.date,
    day_index: observation.day_index,
    condition: observation.condition,
    severity: observation.adverse_event_severity ?? "mild",
    description: observation.adverse_event_description?.trim() || "Logged during check-in.",
  };
}

function event(type: TrialEvent["type"], detail: string): TrialEvent {
  return {
    id: id("evt"),
    type,
    timestamp: new Date().toISOString(),
    detail,
  };
}

function id(prefix: string): string {
  return `${prefix}-${crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`}`;
}

export function stableHash(value: unknown): string {
  const payload = typeof value === "string" ? value : JSON.stringify(value);
  let hash = 2166136261;
  for (let index = 0; index < payload.length; index++) {
    hash ^= payload.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function toLocalDateInput(date: Date): string {
  const local = new Date(date);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 10);
}
