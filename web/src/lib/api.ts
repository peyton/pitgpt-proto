import type { Assignment, IngestionResult, Observation, ResultCard } from "./types";

const BASE = "/api";

export async function ingest(
  query: string,
  documents: string[] = [],
  model?: string,
): Promise<IngestionResult> {
  const res = await fetch(`${BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      documents,
      model: model ?? "anthropic/claude-sonnet-4",
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Ingestion failed");
  }
  return res.json();
}

export async function analyze(
  protocol: Record<string, unknown>,
  observations: Observation[],
): Promise<ResultCard> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ protocol, observations }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Analysis failed");
  }
  return res.json();
}

export async function analyzeExample(): Promise<ResultCard> {
  const res = await fetch(`${BASE}/analyze/example`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Example analysis failed");
  }
  return res.json();
}

export async function generateScheduleApi(
  durationWeeks: number,
  blockLengthDays: number,
  seed: number,
): Promise<Assignment[]> {
  const res = await fetch(`${BASE}/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      duration_weeks: durationWeeks,
      block_length_days: blockLengthDays,
      seed,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Schedule generation failed");
  }
  return res.json();
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
