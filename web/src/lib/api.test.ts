import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ingest, ingestExperimentStream, setApiToken, validateTrial } from "./api";
import type { IngestionResult } from "./types";

const invokeMock = vi.hoisted(() => vi.fn());

vi.mock("@tauri-apps/api/core", () => ({
  invoke: invokeMock,
}));

const ingestionResult: IngestionResult = {
  decision: "block",
  safety_tier: "RED",
  evidence_quality: "weak",
  evidence_conflict: false,
  protocol: null,
  block_reason: "Unsupported request.",
  user_message: "Choose a lower-risk comparison.",
};

function installLocalStorage(): void {
  const store = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
    removeItem: (key: string) => store.delete(key),
    clear: () => store.clear(),
  });
}

function validationResponse(): Response {
  return new Response(JSON.stringify({
    valid: true,
    errors: [],
    warnings: [],
    observation_count: 0,
    planned_days: 7,
    block_length_days: 7,
  }));
}

describe("api", () => {
  beforeEach(() => {
    installLocalStorage();
  });

  afterEach(() => {
    Reflect.deleteProperty(globalThis, "window");
    invokeMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("sends the configured API token to protected endpoints", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      validationResponse(),
    );
    vi.stubGlobal("fetch", fetchMock);
    setApiToken("secret");

    await validateTrial({ planned_days: 7, block_length_days: 7 }, []);

    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.headers).toMatchObject({ Authorization: "Bearer secret" });
  });

  it("falls back to the persisted settings token", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      validationResponse(),
    );
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem("pitgpt_state", JSON.stringify({ settings: { apiToken: "from-state" } }));

    await validateTrial({ planned_days: 7, block_length_days: 7 }, []);

    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.headers).toMatchObject({ Authorization: "Bearer from-state" });
  });

  it("trims and clears the stored API token", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      validationResponse(),
    );
    vi.stubGlobal("fetch", fetchMock);

    setApiToken(" secret ");
    await validateTrial({ planned_days: 7, block_length_days: 7 }, []);
    setApiToken("");
    await validateTrial({ planned_days: 7, block_length_days: 7 }, []);

    expect(fetchMock.mock.calls[0]?.[1]?.headers).toMatchObject({
      Authorization: "Bearer secret",
    });
    expect(fetchMock.mock.calls[1]?.[1]?.headers).toEqual({ "Content-Type": "application/json" });
  });

  it("passes abort signals and auth headers to ingestion fetch requests", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
      return new Response(JSON.stringify(ingestionResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    setApiToken("secret");

    await expect(
      ingest("Compare moisturizers", ["source"], "test-model", "openrouter", {
        signal: controller.signal,
      }),
    ).resolves.toEqual(ingestionResult);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ingest",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer secret" }),
        signal: controller.signal,
      }),
    );
  });

  it("parses streamed experiment setup events", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
      const body = [
        JSON.stringify({ type: "trace", message: "Checking safety boundaries." }),
        JSON.stringify({ type: "result", message: "Done.", result: ingestionResult }),
      ].join("\n");
      return new Response(`${body}\n`, {
        status: 200,
        headers: { "Content-Type": "application/x-ndjson" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const events: unknown[] = [];

    const result = await ingestExperimentStream(
      "Compare moisturizers",
      ["source"],
      "test-model",
      "openrouter",
      (event) => events.push(event),
    );

    expect(result).toEqual(ingestionResult);
    expect(events).toEqual([
      { type: "trace", message: "Checking safety boundaries.", result: null },
      { type: "result", message: "Done.", result: ingestionResult },
    ]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/experiments/ingest-stream",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("emits native setup trace events before returning native ingestion", async () => {
    vi.stubGlobal("window", { __TAURI_INTERNALS__: {} });
    invokeMock.mockResolvedValue(ingestionResult);
    const events: unknown[] = [];

    const result = await ingestExperimentStream(
      "Compare moisturizers",
      [],
      undefined,
      "ollama",
      (event) => events.push(event),
    );

    expect(result).toEqual(ingestionResult);
    expect(events).toContainEqual({ type: "trace", message: "Reading your experiment question." });
    expect(events.at(-1)).toEqual({
      type: "result",
      message: "Experiment setup complete.",
      result: ingestionResult,
    });
    expect(invokeMock).toHaveBeenCalledWith(
      "ingest_local",
      expect.objectContaining({ provider: "ollama" }),
    );
  });

  it("uses structured API error messages when detail is not a string", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({ detail: [{ msg: "bad" }], error: { message: "Request validation failed" } }),
          { status: 422, statusText: "Unprocessable Entity" },
        ),
      ),
    );

    await expect(validateTrial({ planned_days: 0 }, [])).rejects.toThrow(
      "Request validation failed",
    );
  });

  it("does not start ingestion when the signal is already aborted", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn();
    controller.abort();
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      ingest("Compare moisturizers", [], undefined, undefined, { signal: controller.signal }),
    ).rejects.toMatchObject({ name: "AbortError" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("cancels native ingestion through the tauri cancellation command", async () => {
    vi.stubGlobal("window", { __TAURI_INTERNALS__: {} });
    let rejectIngest: ((error: Error) => void) | null = null;
    invokeMock.mockImplementation((command: string) => {
      if (command === "ingest_local") {
        return new Promise((_resolve, reject) => {
          rejectIngest = reject;
        });
      }
      if (command === "cancel_ingest_local") {
        rejectIngest?.(new Error("Ingestion cancelled."));
        return Promise.resolve(true);
      }
      return Promise.reject(new Error(`Unhandled command: ${command}`));
    });

    const controller = new AbortController();
    const result = ingest("Compare moisturizers", [], undefined, "ollama", {
      signal: controller.signal,
    });

    await expect.poll(() => invokeMock.mock.calls.length).toBe(1);
    controller.abort();

    await expect(result).rejects.toMatchObject({ name: "AbortError" });
    expect(invokeMock).toHaveBeenCalledWith(
      "ingest_local",
      expect.objectContaining({ requestId: expect.any(String) }),
    );
    expect(invokeMock).toHaveBeenCalledWith(
      "cancel_ingest_local",
      expect.objectContaining({ requestId: expect.any(String) }),
    );
    const ingestArgs = invokeMock.mock.calls.find(([command]) => command === "ingest_local")?.[1] as
      | Record<string, unknown>
      | undefined;
    const cancelArgs = invokeMock.mock.calls.find(([command]) => command === "cancel_ingest_local")
      ?.[1] as Record<string, unknown> | undefined;
    expect(cancelArgs?.requestId).toBe(ingestArgs?.requestId);
  });

  it("preserves native string rejection messages", async () => {
    vi.stubGlobal("window", { __TAURI_INTERNALS__: {} });
    invokeMock.mockRejectedValue("The model did not return a complete protocol.");

    await expect(ingest("Compare moisturizers", [], undefined, "ollama")).rejects.toThrow(
      "The model did not return a complete protocol.",
    );
  });

  it("uses native validation instead of the old success stub in Tauri", async () => {
    vi.stubGlobal("window", { __TAURI_INTERNALS__: {} });
    invokeMock.mockResolvedValue({
      valid: false,
      errors: ["planned_days must be positive"],
      warnings: [],
      observation_count: 0,
      planned_days: 0,
      block_length_days: 7,
    });

    const result = await validateTrial({ planned_days: 0, block_length_days: 7 }, []);

    expect(invokeMock).toHaveBeenCalledWith("validate_trial", {
      protocol: { planned_days: 0, block_length_days: 7 },
      observations: [],
    });
    expect(result.valid).toBe(false);
    expect(result.errors).toContain("planned_days must be positive");
  });
});
