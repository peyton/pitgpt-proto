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
  _blockLengthDays: number,
  seed: number,
): Assignment[] {
  const rng = mulberry32(seed);
  const numPairs = Math.floor(durationWeeks / 2);
  const schedule: Assignment[] = [];

  for (let pair = 0; pair < numPairs; pair++) {
    const aFirst = rng() < 0.5;
    const w1 = pair * 2;
    const w2 = pair * 2 + 1;
    schedule.push(
      { week: w1, condition: aFirst ? "A" : "B" },
      { week: w2, condition: aFirst ? "B" : "A" },
    );
  }

  // Handle odd week
  if (durationWeeks % 2 === 1) {
    schedule.push({
      week: durationWeeks - 1,
      condition: rng() < 0.5 ? "A" : "B",
    });
  }

  return schedule;
}

export function generateSeed(): number {
  return Math.floor(Math.random() * 2147483647);
}
