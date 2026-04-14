import { afterEach, describe, expect, it, vi } from "vitest";
import { ingest } from "./api";
import type { IngestionResult } from "./types";

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
});
