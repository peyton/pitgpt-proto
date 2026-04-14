import { afterEach, describe, expect, it, vi } from "vitest";
import { ingest } from "./api";
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

describe("api", () => {
  afterEach(() => {
    Reflect.deleteProperty(globalThis, "window");
    invokeMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("passes abort signals to ingestion fetch requests", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
      return new Response(JSON.stringify(ingestionResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      ingest("Compare moisturizers", ["source"], "test-model", "openrouter", {
        signal: controller.signal,
      }),
    ).resolves.toEqual(ingestionResult);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ingest",
      expect.objectContaining({ signal: controller.signal }),
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
});
