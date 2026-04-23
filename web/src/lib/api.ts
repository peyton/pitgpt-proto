import { isTauriRuntime, invokeNative } from "./runtime";
import type {
  AiProviderInfo,
  AiProviderKind,
  Assignment,
  IngestionResult,
  Observation,
  ResultCard,
  ValidationReport,
  WorkflowDefinition,
  WorkflowDemoPayload,
} from "./types";

const BASE = "/api";
const TOKEN_KEY = "pitgpt_api_token";
const STATE_KEY = "pitgpt_state";

export function setApiToken(token: string): void {
  const trimmed = token.trim();
  if (trimmed) {
    localStorage.setItem(TOKEN_KEY, trimmed);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
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
    return typeof parsed.settings?.apiToken === "string" ? parsed.settings.apiToken.trim() : "";
  } catch {
    return "";
  }
}

interface ApiRequestOptions {
  signal?: AbortSignal;
  workflowId?: string;
}

export interface IngestStreamEvent {
  type: "trace" | "result" | "error";
  message: string;
  result?: IngestionResult | null;
}

export async function ingest(
  query: string,
  documents: string[] = [],
  model?: string,
  provider?: AiProviderKind,
  options: ApiRequestOptions = {},
): Promise<IngestionResult> {
  throwIfAborted(options.signal);
  if (isTauriRuntime()) {
    return ingestNative(query, documents, model, provider, options);
  }
  const res = await fetch(`${BASE}/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    signal: options.signal,
    body: JSON.stringify({
      query,
      documents,
      model: model ?? "anthropic/claude-sonnet-4",
      provider,
      workflow_id: options.workflowId,
    }),
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Ingestion failed"));
  }
  return res.json();
}

export async function ingestExperimentStream(
  query: string,
  documents: string[] = [],
  model: string | undefined,
  provider: AiProviderKind | undefined,
  onEvent: (event: IngestStreamEvent) => void,
  options: ApiRequestOptions = {},
): Promise<IngestionResult> {
  throwIfAborted(options.signal);
  if (isTauriRuntime()) {
    return ingestNativeWithTrace(query, documents, model, provider, onEvent, options);
  }

  const res = await fetch(`${BASE}/experiments/ingest-stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    signal: options.signal,
    body: JSON.stringify({
      query,
      documents,
      model: model ?? "anthropic/claude-sonnet-4",
      provider,
      workflow_id: options.workflowId,
    }),
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Experiment setup failed"));
  }
  if (!res.body) {
    const result = await ingest(query, documents, model, provider, options);
    onEvent({ type: "result", message: "Experiment setup complete.", result });
    return result;
  }

  let finalResult: IngestionResult | null = null;
  let buffer = "";
  const decoder = new TextDecoder();
  const reader = res.body.getReader();
  try {
    while (true) {
      throwIfAborted(options.signal);
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const event = parseStreamEvent(line);
        if (!event) continue;
        onEvent(event);
        if (event.type === "error") throw new Error(event.message);
        if (event.type === "result" && event.result) finalResult = event.result;
      }
    }
  } finally {
    reader.releaseLock();
  }
  const trailing = parseStreamEvent(buffer);
  if (trailing) {
    onEvent(trailing);
    if (trailing.type === "error") throw new Error(trailing.message);
    if (trailing.type === "result" && trailing.result) finalResult = trailing.result;
  }
  if (!finalResult) throw new Error("Experiment setup ended without a result.");
  return finalResult;
}

async function ingestNativeWithTrace(
  query: string,
  documents: string[],
  model: string | undefined,
  provider: AiProviderKind | undefined,
  onEvent: (event: IngestStreamEvent) => void,
  options: ApiRequestOptions,
): Promise<IngestionResult> {
  onEvent({ type: "trace", message: "Reading your experiment question." });
  if (documents.length > 0) {
    onEvent({ type: "trace", message: `Reviewing ${documents.length} attached source(s).` });
  }
  onEvent({ type: "trace", message: "Checking safety boundaries and trial fit." });
  onEvent({ type: "trace", message: "Drafting follow-up questions or a protocol." });
  const result = await ingest(query, documents, model, provider, options);
  if (result.decision === "manual_review_before_protocol") {
    onEvent({ type: "trace", message: "Follow-up questions are ready." });
  } else if (result.decision === "block") {
    onEvent({ type: "trace", message: "This request is outside the supported experiment scope." });
  } else {
    onEvent({ type: "trace", message: "Protocol draft is ready for review." });
  }
  onEvent({ type: "result", message: "Experiment setup complete.", result });
  return result;
}

function parseStreamEvent(line: string): IngestStreamEvent | null {
  const trimmed = line.trim();
  if (!trimmed) return null;
  const parsed = JSON.parse(trimmed) as Partial<IngestStreamEvent>;
  if (
    (parsed.type === "trace" || parsed.type === "result" || parsed.type === "error") &&
    typeof parsed.message === "string"
  ) {
    return {
      type: parsed.type,
      message: parsed.message,
      result: parsed.result ?? null,
    };
  }
  return null;
}

async function ingestNative(
  query: string,
  documents: string[],
  model: string | undefined,
  provider: AiProviderKind | undefined,
  options: ApiRequestOptions,
): Promise<IngestionResult> {
  const requestId = options.signal ? requestIdForNativeIngest() : null;
  const cancelNative = () => {
    if (!requestId) return;
    void invokeNative<boolean>("cancel_ingest_local", { requestId }).catch(() => undefined);
  };
  options.signal?.addEventListener("abort", cancelNative, { once: true });
  try {
    const result = await invokeNative<IngestionResult>("ingest_local", {
      query,
      documents,
      provider: provider ?? "ollama",
      model: model || null,
      workflowId: options.workflowId ?? null,
      requestId,
    });
    throwIfAborted(options.signal);
    return result;
  } catch (error) {
    if (options.signal?.aborted || isNativeCancellationError(error)) {
      throwAbortError();
    }
    throw error;
  } finally {
    options.signal?.removeEventListener("abort", cancelNative);
  }
}

function throwIfAborted(signal?: AbortSignal): void {
  if (!signal?.aborted) return;
  throwAbortError();
}

function throwAbortError(): never {
  const error = new Error("Request aborted.");
  error.name = "AbortError";
  throw error;
}

function requestIdForNativeIngest(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function isNativeCancellationError(error: unknown): boolean {
  return error instanceof Error && error.message.includes("Ingestion cancelled.");
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
    throw new Error(await readErrorMessage(res, "Analysis failed"));
  }
  return res.json();
}

export async function validateTrial(
  protocol: Record<string, unknown>,
  observations: Observation[],
): Promise<ValidationReport> {
  if (isTauriRuntime()) {
    return invokeNative<ValidationReport>("validate_trial", { protocol, observations });
  }
  const res = await fetch(`${BASE}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ protocol, observations }),
  });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Validation failed"));
  }
  return res.json();
}

export async function analyzeExample(): Promise<ResultCard> {
  if (isTauriRuntime()) {
    return invokeNative<ResultCard>("analyze_example");
  }
  const res = await fetch(`${BASE}/analyze/example`, { headers: authHeaders() });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Example analysis failed"));
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
    throw new Error(await readErrorMessage(res, "Schedule generation failed"));
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
  try {
    const res = await fetch(`${BASE}/providers`, { headers: authHeaders() });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export async function listWorkflows(): Promise<WorkflowDefinition[]> {
  if (isTauriRuntime()) {
    return invokeNative<WorkflowDefinition[]>("list_workflows");
  }
  const res = await fetch(`${BASE}/workflows`, { headers: authHeaders() });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Could not load workflows"));
  }
  return res.json();
}

export async function getWorkflowDemo(workflowId: string): Promise<WorkflowDemoPayload> {
  if (isTauriRuntime()) {
    const workflows = await listWorkflows();
    const workflow = workflows.find((item) => item.id === workflowId);
    if (!workflow) throw new Error(`Workflow ${workflowId} not found.`);
    return {
      workflow_id: workflow.id,
      query: workflow.demo.query,
      documents: workflow.demo.documents,
      recommended_provider: workflow.recommended_provider,
      recommended_model: workflow.recommended_models[workflow.recommended_provider] ?? "",
    };
  }
  const res = await fetch(`${BASE}/workflows/${workflowId}/demo`, { headers: authHeaders() });
  if (!res.ok) {
    throw new Error(await readErrorMessage(res, "Could not load workflow demo"));
  }
  return res.json();
}

async function readErrorMessage(res: Response, fallback: string): Promise<string> {
  const err = await res.json().catch(() => null) as { detail?: unknown; error?: { message?: unknown } } | null;
  if (typeof err?.detail === "string" && err.detail.trim()) return err.detail;
  if (typeof err?.error?.message === "string" && err.error.message.trim()) return err.error.message;
  if (res.statusText) return res.statusText;
  return fallback;
}
