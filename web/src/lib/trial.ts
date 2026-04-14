import type { AdverseEvent, Assignment, IngestionResult, Observation, Protocol, Trial, TrialEvent } from "./types";
import { generateSchedule, generateSeed } from "./randomize";

export function createTrial(
  ingestion: IngestionResult,
  conditionALabel: string,
  conditionBLabel: string,
): Trial {
  const protocol = ingestion.protocol!;
  protocol.condition_a_label = conditionALabel;
  protocol.condition_b_label = conditionBLabel;
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
    secondaryScores?: Record<string, number>;
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
    secondaryScores?: Record<string, number>;
  } = {},
): Observation {
  const date = parseDateInput(dateStr);
  const dayIndex = getTrialDayIndexForDate(trial, date);
  const assignment = getAssignmentForDay(trial, dayIndex);
  const backfillDays = getBackfillDays(dateStr);

  return {
    observation_id: id("obs"),
    day_index: dayIndex,
    date: dateStr,
    condition: assignment?.condition ?? "A",
    assigned_condition: assignment?.condition ?? null,
    actual_condition: assignment?.condition ?? "A",
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
    secondary_scores: options.secondaryScores ?? {},
    recorded_at: new Date().toISOString(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "local",
    planned_checkin_time: "",
    minutes_from_planned_checkin: null,
    deviation_codes: [],
    confounders: {},
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
    primary_outcome: protocol.primary_outcome ?? null,
    analysis_plan: {
      method_version: "2026-04-14-paired-primary-v1",
      primary_method: "paired_blocks",
      fallback_method: "welch",
      denominator_policy: "planned_days",
    },
    duration_weeks: protocol.duration_weeks,
    cadence: protocol.cadence,
    washout: protocol.washout,
    primary_outcome_question: protocol.primary_outcome_question,
    condition_a_label: protocol.condition_a_label ?? "Condition A",
    condition_b_label: protocol.condition_b_label ?? "Condition B",
    secondary_outcomes: protocol.secondary_outcomes ?? [],
    amendments: protocol.amendments ?? [],
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
  const payload = {
    protocol: trial.protocol,
    schedule: trial.schedule,
    seed: trial.seed,
    conditionALabel: trial.conditionALabel,
    conditionBLabel: trial.conditionBLabel,
    protocolHash: trial.protocolHash,
    analysisPlanHash: trial.analysisPlanHash,
  };
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
  return sha256Hex(canonicalJson(value));
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(canonicalize(value)) ?? "null";
}

function canonicalize(value: unknown): unknown {
  if (value === null || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map((item) => item === undefined ? null : canonicalize(item));
  const output: Record<string, unknown> = {};
  for (const key of Object.keys(value).sort()) {
    const item = (value as Record<string, unknown>)[key];
    if (item !== undefined) output[key] = canonicalize(item);
  }
  return output;
}

const SHA256_K = new Uint32Array([
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
]);

function sha256Hex(input: string): string {
  const bytes = new TextEncoder().encode(input);
  const bitLength = bytes.length * 8;
  const totalLength = bytes.length + 1 + ((64 - ((bytes.length + 1 + 8) % 64)) % 64) + 8;
  const data = new Uint8Array(totalLength);
  data.set(bytes);
  data[bytes.length] = 0x80;
  const view = new DataView(data.buffer);
  view.setUint32(totalLength - 8, Math.floor(bitLength / 0x100000000));
  view.setUint32(totalLength - 4, bitLength >>> 0);

  const hash = new Uint32Array([
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
  ]);
  const words = new Uint32Array(64);

  for (let offset = 0; offset < data.length; offset += 64) {
    for (let index = 0; index < 16; index++) {
      words[index] = view.getUint32(offset + index * 4);
    }
    for (let index = 16; index < 64; index++) {
      words[index] = (
        smallSigma1(wordAt(words, index - 2)) +
        wordAt(words, index - 7) +
        smallSigma0(wordAt(words, index - 15)) +
        wordAt(words, index - 16)
      ) >>> 0;
    }

    let a = wordAt(hash, 0);
    let b = wordAt(hash, 1);
    let c = wordAt(hash, 2);
    let d = wordAt(hash, 3);
    let e = wordAt(hash, 4);
    let f = wordAt(hash, 5);
    let g = wordAt(hash, 6);
    let h = wordAt(hash, 7);

    for (let index = 0; index < 64; index++) {
      const temp1 = (
        h +
        bigSigma1(e) +
        choose(e, f, g) +
        wordAt(SHA256_K, index) +
        wordAt(words, index)
      ) >>> 0;
      const temp2 = (bigSigma0(a) + majority(a, b, c)) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + temp1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (temp1 + temp2) >>> 0;
    }

    hash[0] = (wordAt(hash, 0) + a) >>> 0;
    hash[1] = (wordAt(hash, 1) + b) >>> 0;
    hash[2] = (wordAt(hash, 2) + c) >>> 0;
    hash[3] = (wordAt(hash, 3) + d) >>> 0;
    hash[4] = (wordAt(hash, 4) + e) >>> 0;
    hash[5] = (wordAt(hash, 5) + f) >>> 0;
    hash[6] = (wordAt(hash, 6) + g) >>> 0;
    hash[7] = (wordAt(hash, 7) + h) >>> 0;
  }

  return Array.from(hash, (word) => word.toString(16).padStart(8, "0")).join("");
}

function wordAt(words: Uint32Array, index: number): number {
  return words[index] ?? 0;
}

function rotateRight(value: number, bits: number): number {
  return (value >>> bits) | (value << (32 - bits));
}

function choose(x: number, y: number, z: number): number {
  return (x & y) ^ (~x & z);
}

function majority(x: number, y: number, z: number): number {
  return (x & y) ^ (x & z) ^ (y & z);
}

function bigSigma0(value: number): number {
  return rotateRight(value, 2) ^ rotateRight(value, 13) ^ rotateRight(value, 22);
}

function bigSigma1(value: number): number {
  return rotateRight(value, 6) ^ rotateRight(value, 11) ^ rotateRight(value, 25);
}

function smallSigma0(value: number): number {
  return rotateRight(value, 7) ^ rotateRight(value, 18) ^ (value >>> 3);
}

function smallSigma1(value: number): number {
  return rotateRight(value, 17) ^ rotateRight(value, 19) ^ (value >>> 10);
}

function toLocalDateInput(date: Date): string {
  const local = new Date(date);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 10);
}
