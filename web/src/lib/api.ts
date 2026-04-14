import { isTauriRuntime, invokeNative } from "./runtime";
import type {
  AiProviderInfo,
  AiProviderKind,
  Assignment,
  IngestionResult,
  Observation,
  ResultCard,
  ValidationReport,
} from "./types";

const BASE = "/api";
const TOKEN_KEY = "pitgpt_api_token";
const STATE_KEY = "pitgpt_state";

export function setApiToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem(TOKEN_KEY) || readTokenFromState();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function readTokenFromState(): string {
  try {
    const raw = localStorage.getItem(STATE_KEY);
    if (!raw) return "";
    const parsed = JSON.parse(raw) as { settings?: { apiToken?: unknown } };
    return typeof parsed.settings?.apiToken === "string" ? parsed.settings.apiToken : "";
  } catch {
    return "";
  }
}

export async function ingest(
  query: string,
  documents: string[] = [],
  model?: string,
  provider?: AiProviderKind,
): Promise<IngestionResult> {
  if (isTauriRuntime()) {
    return invokeNative<IngestionResult>("ingest_local", {
      query,
      documents,
      provider: provider ?? "ollama",
      model: model || null,
    });
  }
  const res = await fetch(`${BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({
      query,
      documents,
      model: model ?? "anthropic/claude-sonnet-4",
      provider,
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
  if (isTauriRuntime()) {
    return invokeNative<ResultCard>("analyze", { protocol, observations });
  }
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ protocol, observations }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Analysis failed");
  }
  return res.json();
}

export async function validateTrial(
  protocol: Record<string, unknown>,
  observations: Observation[],
): Promise<ValidationReport> {
  if (isTauriRuntime()) {
    return {
      valid: true,
      errors: [],
      warnings: [],
      observation_count: observations.length,
      planned_days:
        typeof protocol.planned_days === "number" ? protocol.planned_days : null,
      block_length_days:
        typeof protocol.block_length_days === "number" ? protocol.block_length_days : null,
    };
  }
  const res = await fetch(`${BASE}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ protocol, observations }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Validation failed");
  }
  return res.json();
}

export async function analyzeExample(): Promise<ResultCard> {
  if (isTauriRuntime()) {
    return invokeNative<ResultCard>("analyze_example");
  }
  const res = await fetch(`${BASE}/analyze/example`, { headers: authHeaders() });
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
  if (isTauriRuntime()) {
    return invokeNative<Assignment[]>("generate_schedule", {
      durationWeeks,
      blockLengthDays,
      seed,
    });
  }
  const res = await fetch(`${BASE}/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
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
  if (isTauriRuntime()) return true;
  try {
    const res = await fetch(`${BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function listProviders(): Promise<AiProviderInfo[]> {
  if (isTauriRuntime()) {
    return invokeNative<AiProviderInfo[]>("discover_ai_tools");
  }
  const res = await fetch(`${BASE}/providers`, { headers: authHeaders() });
  if (!res.ok) return [];
  return res.json();
}
