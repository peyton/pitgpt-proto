import type { Assignment } from "./types";

/** Mulberry32 — deterministic 32-bit PRNG */
function mulberry32(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Generate a block-randomized A/B schedule.
 *
 * Each "block" is a pair of periods (e.g., 2 weeks). Within each block,
 * one period is randomly assigned A and the other B. This ensures balanced
 * exposure while controlling for time trends.
 */
export function generateSchedule(
  durationWeeks: number,
  blockLengthDays: number,
  seed: number,
): Assignment[] {
  if (durationWeeks <= 0) throw new Error("durationWeeks must be positive");
  if (blockLengthDays <= 0) throw new Error("blockLengthDays must be positive");

  const rng = mulberry32(seed);
  const totalDays = durationWeeks * 7;
  const periodCount = getPeriodCount(durationWeeks, blockLengthDays);
  const schedule: Assignment[] = [];

  for (let pair = 0; pair < Math.ceil(periodCount / 2); pair++) {
    const aFirst = rng() < 0.5;
    const conditions: Array<"A" | "B"> = aFirst ? ["A", "B"] : ["B", "A"];

    for (const [offset, condition] of conditions.entries()) {
      const periodIndex = pair * 2 + offset;
      if (periodIndex >= periodCount) break;
      const startDay = periodIndex * blockLengthDays + 1;
      const endDay = Math.min(totalDays, startDay + blockLengthDays - 1);
      schedule.push({
        period_index: periodIndex,
        pair_index: pair,
        condition,
        start_day: startDay,
        end_day: endDay,
        week: periodIndex,
      });
    }
  }

  return schedule;
}

export function generateSeed(): number {
  if (typeof crypto !== "undefined" && crypto.getRandomValues) {
    const values = new Uint32Array(1);
    crypto.getRandomValues(values);
    return (values[0] ?? 0) % 2147483647;
  }
  return Math.floor(Math.random() * 2147483647);
}

export function getPeriodCount(durationWeeks: number, blockLengthDays: number): number {
  if (durationWeeks <= 0 || blockLengthDays <= 0) return 0;
  return Math.ceil((durationWeeks * 7) / blockLengthDays);
}
