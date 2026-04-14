import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setApiToken, validateTrial } from "./api";

function installLocalStorage() {
  const store = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
    removeItem: (key: string) => store.delete(key),
    clear: () => store.clear(),
  });
}

describe("api auth headers", () => {
  beforeEach(() => {
    installLocalStorage();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the configured API token to protected endpoints", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({
      valid: true,
      errors: [],
      warnings: [],
      observation_count: 0,
      planned_days: 7,
      block_length_days: 7,
    })));
    vi.stubGlobal("fetch", fetchMock);
    setApiToken("secret");

    await validateTrial({ planned_days: 7, block_length_days: 7 }, []);

    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.headers).toMatchObject({ Authorization: "Bearer secret" });
  });

  it("falls back to the persisted settings token", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => new Response(JSON.stringify({
      valid: true,
      errors: [],
      warnings: [],
      observation_count: 0,
      planned_days: 7,
      block_length_days: 7,
    })));
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem("pitgpt_state", JSON.stringify({ settings: { apiToken: "from-state" } }));

    await validateTrial({ planned_days: 7, block_length_days: 7 }, []);

    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.headers).toMatchObject({ Authorization: "Bearer from-state" });
  });
});
