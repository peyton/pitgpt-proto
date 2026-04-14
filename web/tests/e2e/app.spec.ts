import { expect, test, type Page, type Route, type TestInfo } from "@playwright/test";

const protocol = {
  template: "Skincare Product",
  duration_weeks: 6,
  block_length_days: 7,
  cadence: "daily",
  washout: "None",
  primary_outcome_question: "Skin satisfaction (0-10)",
  screening: "",
  warnings: "",
};

const generatedIngestion = {
  decision: "generate_protocol",
  safety_tier: "GREEN",
  evidence_quality: "moderate",
  evidence_conflict: false,
  protocol,
  block_reason: null,
  user_message: "Ready to compare two everyday products.",
};

const analysisResult = {
  quality_grade: "C",
  verdict: "favors_a",
  mean_a: 7,
  mean_b: 5,
  difference: 2,
  ci_lower: 0.4,
  ci_upper: 3.6,
  cohens_d: 1.1,
  n_used_a: 1,
  n_used_b: 1,
  adherence_rate: 1,
  days_logged_pct: 0.5,
  early_stop: true,
  late_backfill_excluded: 0,
  block_breakdown: [],
  sensitivity_excluding_partial: null,
  planned_days_defaulted: false,
  summary: "Condition A scored higher in the data collected so far.",
  caveats: "This was stopped early, so interpret the result cautiously.",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok" }),
    });
  });
  await mockProviders(page, []);
});

test("query and source upload flow reaches results", async ({ page }) => {
  let ingestBody: Record<string, unknown> | null = null;
  let analyzeBody: Record<string, unknown> | null = null;

  await page.route("**/api/ingest", async (route) => {
    ingestBody = JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(generatedIngestion),
    });
  });
  await page.route("**/api/analyze", async (route) => {
    analyzeBody = JSON.parse(route.request().postData() ?? "{}") as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(analysisResult),
    });
  });

  await page.goto("/");
  await page.getByLabel("Experiment question").fill("Compare CeraVe and La Roche-Posay");
  await page.locator('input[type="file"]').setInputFiles({
    name: "study.md",
    mimeType: "text/markdown",
    buffer: Buffer.from("A small cosmetic study reports comfort outcomes."),
  });
  await expect(page.getByText("study.md")).toBeVisible();

  await page.getByLabel("Generate protocol").click();
  await expect(page.getByRole("heading", { name: "Generated Protocol" })).toBeVisible();
  expect(ingestBody?.query).toBe("Compare CeraVe and La Roche-Posay");
  expect(ingestBody?.documents).toEqual(["A small cosmetic study reports comfort outcomes."]);

  await page.getByPlaceholder("CeraVe Moisturizing Cream").fill("CeraVe");
  await page.getByPlaceholder("La Roche-Posay Toleriane").fill("La Roche-Posay");
  await page.getByRole("button", { name: "Lock Protocol & Start" }).click();

  await expect(page.getByRole("heading", { name: /CeraVe vs. La Roche-Posay/ })).toBeVisible();
  await page.getByRole("button", { name: "Submit Check-In" }).click();
  await expect(page.getByText("Today's check-in submitted!")).toBeVisible();

  await page.getByRole("button", { name: "Stop Experiment Early" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Stop and Analyze" }).click();
  await expect(page.getByRole("heading", { name: /CeraVe vs. La Roche-Posay/ })).toBeVisible();
  await expect(page.getByText("Evidence Basis")).toBeVisible();
  await expect(page.getByText("Late Backfills Excluded")).toBeVisible();

  const observations = (analyzeBody?.observations ?? []) as unknown[];
  expect(observations).toHaveLength(1);
});

test("generation can be stopped before ingest completes", async ({ page }) => {
  let releaseIngest: (() => void) | null = null;
  let ingestRequests = 0;

  await page.route("**/api/ingest", async (route) => {
    ingestRequests += 1;
    await new Promise<void>((resolve) => {
      releaseIngest = resolve;
    });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(generatedIngestion),
    }).catch(() => undefined);
  });

  await page.goto("/");
  await page.getByLabel("Experiment question").fill("Compare CeraVe and La Roche-Posay");
  await page.getByLabel("Generate protocol").click();

  await expect(page.getByLabel("Stop generation")).toBeVisible();
  await expect(page.getByLabel("Experiment question")).toBeDisabled();

  await page.getByLabel("Stop generation").click();

  await expect(page.getByLabel("Generate protocol")).toBeVisible();
  await expect(page.getByLabel("Experiment question")).toBeEnabled();
  expect(ingestRequests).toBe(1);

  releaseIngest?.();
  await expect(page.getByRole("heading", { name: "What do you want to test?" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Generated Protocol" })).toHaveCount(0);
});

test("local template starts without calling ingest", async ({ page }) => {
  let ingestCalled = false;
  await page.route("**/api/ingest", async (route) => {
    ingestCalled = true;
    await route.abort();
  });

  await page.goto("/");
  await page.getByRole("button", { name: /Sleep Routine/ }).click();

  await expect(page.getByRole("heading", { name: "Generated Protocol" })).toBeVisible();
  await expect(page.getByText("Sleep Routine").first()).toBeVisible();
  expect(ingestCalled).toBe(false);
});

test("blocked and manual-review ingestion responses are gated", async ({ page }) => {
  await mockIngest(page, {
    decision: "block",
    safety_tier: "RED",
    evidence_quality: "weak",
    evidence_conflict: false,
    protocol: null,
    block_reason: "This comparison is outside the supported scope.",
    user_message: "Choose an everyday routine or product comparison.",
  });

  await page.goto("/");
  await page.getByLabel("Experiment question").fill("Compare prescription timing");
  await page.getByLabel("Generate protocol").click();
  await expect(page.getByRole("heading", { name: "Experiment Blocked" })).toBeVisible();

  await mockIngest(page, {
    decision: "manual_review_before_protocol",
    safety_tier: "YELLOW",
    evidence_quality: "weak",
    evidence_conflict: false,
    protocol: null,
    block_reason: "The active ingredient needs review.",
    user_message: "This source is not ready for a locked protocol.",
  });

  await page.getByRole("button", { name: "Try a Different Question" }).click();
  await page.getByLabel("Experiment question").fill("Compare unclear cosmetic active");
  await page.getByLabel("Generate protocol").click();
  await expect(page.getByRole("heading", { name: "Manual Review Needed" })).toBeVisible();
  await expect(page.getByText("Protocol not ready to lock")).toBeVisible();
});

test("yellow protocol requires acknowledgement before starting", async ({ page }) => {
  await mockIngest(page, {
    ...generatedIngestion,
    decision: "generate_protocol_with_restrictions",
    safety_tier: "YELLOW",
    evidence_quality: "weak",
    protocol: {
      ...protocol,
      template: "Custom A/B",
      screening: "Do not use on broken or irritated skin.",
      warnings: "Stop if irritation persists.",
    },
    user_message: "Allowed only with restrictions.",
  });

  await page.goto("/");
  await page.getByLabel("Experiment question").fill("Compare two cosmetic actives");
  await page.getByLabel("Generate protocol").click();

  const start = page.getByRole("button", { name: "Lock Protocol & Start" });
  await expect(start).toBeDisabled();
  await page.getByRole("checkbox").check();
  await expect(start).toBeEnabled();
  await start.click();
  await expect(page.getByText("Today's Assignment")).toBeVisible();
});

test("backfill accepts only the last two days and records metadata", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Custom A\/B/ }).click();
  await page.getByRole("button", { name: "Lock Protocol & Start" }).click();
  await page.evaluate((createdAt) => {
    const raw = window.localStorage.getItem("pitgpt_state");
    if (!raw) throw new Error("missing app state");
    const state = JSON.parse(raw) as { trial?: { createdAt?: string } };
    if (!state.trial) throw new Error("missing trial");
    state.trial.createdAt = createdAt;
    window.localStorage.setItem("pitgpt_state", JSON.stringify(state));
  }, dateOffset(-2) + "T00:00:00.000Z");
  await page.reload();
  await page.getByText("Backfill recent day").click();

  await page.getByLabel("Backfill date").fill(dateOffset(-3));
  await page.getByRole("button", { name: "Add Backfill" }).click();
  await expect(page.getByRole("alert")).toHaveText("Backfill is limited to the last 2 days.");

  await page.getByLabel("Backfill date").fill(dateOffset(-1));
  await page.getByRole("button", { name: "Add Backfill" }).click();
  await expect(page.getByRole("status")).toHaveText("Backfill saved.");

  const observations = await page.evaluate(() => {
    const raw = window.localStorage.getItem("pitgpt_state");
    return raw ? JSON.parse(raw).trial.observations : [];
  });
  expect(observations).toHaveLength(1);
  expect(observations[0].is_backfill).toBe("yes");
  expect(observations[0].backfill_days).toBe(1);
});

test("settings persist reminders and delete data clears state", async ({ page }, testInfo) => {
  await page.goto("/");
  await goToSettings(page, testInfo);

  await expect(page.getByText("Local API is reachable")).toBeVisible();
  await page.getByLabel("Toggle daily reminder").click();
  await page.locator('input[type="time"]').fill("00:00");

  await expect
    .poll(async () =>
      page.evaluate(() => {
        const raw = window.localStorage.getItem("pitgpt_state");
        return raw ? JSON.parse(raw).settings : null;
      }),
    )
    .toMatchObject({ reminderEnabled: false, reminderTime: "00:00" });

  await page.getByRole("button", { name: "Delete All Data" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Delete All Data" }).click();

  const state = await page.evaluate(() => {
    const raw = window.localStorage.getItem("pitgpt_state");
    return raw ? JSON.parse(raw) : null;
  });
  expect(state.trial).toBeNull();
  expect(state.completedResults).toHaveLength(0);
});

test("settings selects an available local provider", async ({ page }, testInfo) => {
  await mockProviders(page, [
    {
      kind: "openrouter",
      status: "installed_unavailable",
      label: "OpenRouter",
      is_local: false,
      is_offline: false,
      models: [],
      detail: "Set OPENROUTER_API_KEY to use hosted models.",
    },
    {
      kind: "ollama",
      status: "available",
      label: "Ollama",
      is_local: true,
      is_offline: true,
      models: ["llama3.1:latest", "mistral:latest"],
      detail: "Ollama is running.",
    },
    {
      kind: "ios_on_device",
      status: "reserved",
      label: "iOS On-Device",
      is_local: true,
      is_offline: true,
      models: [],
      detail: "On-device models are planned for a later release.",
    },
  ]);

  await page.goto("/");
  await goToSettings(page, testInfo);

  await expect(page.getByText("Ollama is running.")).toBeVisible();
  await page.locator(".provider-row", { hasText: "Ollama" }).getByRole("button", { name: "Use" }).click();

  const settings = await page.evaluate(() => {
    const raw = window.localStorage.getItem("pitgpt_state");
    return raw ? JSON.parse(raw).settings : null;
  });
  expect(settings.preferredProvider).toBe("ollama");
  expect(settings.preferredModel).toBe("llama3.1:latest");
});

test("mocked tauri runtime discovers providers and saves native settings", async ({ page }, testInfo) => {
  await mockTauriRuntime(page);
  await page.goto("/");
  await goToSettings(page, testInfo);

  await expect(page.getByText("desktop")).toBeVisible();
  await expect(page.getByText("Ollama is running.")).toBeVisible();
  await page.locator(".provider-row", { hasText: "Ollama" }).getByRole("button", { name: "Use" }).click();

  await expect
    .poll(async () =>
      page.evaluate(() => {
        const win = window as typeof window & { __TAURI_STATE__?: { settings?: Record<string, unknown> } };
        return win.__TAURI_STATE__?.settings;
      }),
    )
    .toMatchObject({
      preferredProvider: "ollama",
      preferredModel: "llama3.1:latest",
    });
});

test("mocked tauri runtime cancels native ingestion", async ({ page }) => {
  await mockTauriRuntime(page);
  await page.goto("/");

  await page.getByLabel("Experiment question").fill("Compare CeraVe and La Roche-Posay");
  await page.getByLabel("Generate protocol").click();
  await expect(page.getByLabel("Stop generation")).toBeVisible();
  await page.getByLabel("Stop generation").click();

  await expect(page.getByLabel("Generate protocol")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Generated Protocol" })).toHaveCount(0);

  const nativeState = await page.evaluate(() => {
    const win = window as typeof window & {
      __TAURI_CANCEL__?: Record<string, unknown>;
      __TAURI_INGEST_ARGS__?: Record<string, unknown>;
    };
    return {
      cancel: win.__TAURI_CANCEL__,
      ingest: win.__TAURI_INGEST_ARGS__,
    };
  });
  expect(nativeState.ingest?.requestId).toEqual(expect.any(String));
  expect(nativeState.cancel?.requestId).toBe(nativeState.ingest?.requestId);
});

test("mobile sidebar opens navigation", async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== "mobile", "mobile-only navigation check");

  await page.goto("/");
  await page.getByLabel("Menu").click();
  await page.getByRole("link", { name: "Settings" }).click();
  await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
});

async function mockIngest(page: Page, body: unknown): Promise<void> {
  await page.unroute("**/api/ingest").catch(() => undefined);
  await page.route("**/api/ingest", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

async function mockProviders(page: Page, body: unknown): Promise<void> {
  await page.unroute("**/api/providers").catch(() => undefined);
  await page.unroute("**/providers").catch(() => undefined);
  const providerResponse = async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  };
  await page.route("**/api/providers", providerResponse);
  await page.route("**/providers", providerResponse);
}

async function mockTauriRuntime(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.__TAURI_INTERNALS__ = {};
  });
  const moduleBody = `
    const providers = ${JSON.stringify([
      {
        kind: "ollama",
        status: "available",
        label: "Ollama",
        is_local: true,
        is_offline: true,
        models: ["llama3.1:latest"],
        detail: "Ollama is running.",
      },
      {
        kind: "ios_on_device",
        status: "reserved",
        label: "iOS On-Device Models",
        is_local: true,
        is_offline: true,
        models: [],
        detail: "Reserved for future on-device model runtime work.",
      },
    ])};
    export async function invoke(command, args = {}) {
      window.__TAURI_CALLS__ = [...(window.__TAURI_CALLS__ || []), { command, args }];
      if (command === "load_app_state") return window.__TAURI_STATE__ || null;
      if (command === "save_app_state") {
        window.__TAURI_STATE__ = args.state;
        return null;
      }
      if (command === "clear_app_state") {
        window.__TAURI_STATE__ = null;
        return null;
      }
      if (command === "discover_ai_tools") return providers;
      if (command === "export_file") {
        window.__TAURI_EXPORT__ = args;
        return "/tmp/" + args.filename;
      }
      if (command === "analyze") return ${JSON.stringify(analysisResult)};
      if (command === "analyze_example") return ${JSON.stringify(analysisResult)};
      if (command === "generate_schedule") return [];
      if (command === "ingest_local") {
        window.__TAURI_INGEST_ARGS__ = args;
        return new Promise((_resolve, reject) => {
          window.__TAURI_INGEST_REJECT__ = reject;
        });
      }
      if (command === "cancel_ingest_local") {
        window.__TAURI_CANCEL__ = args;
        window.__TAURI_INGEST_REJECT__?.(new Error("Ingestion cancelled."));
        return true;
      }
      throw new Error("Unhandled Tauri command: " + command);
    }
  `;
  await page.route("**/*tauri-apps_api_core*.js*", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/javascript", body: moduleBody });
  });
  await page.route("**/*@tauri-apps*core*.js*", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/javascript", body: moduleBody });
  });
}

async function goToSettings(page: Page, testInfo: TestInfo): Promise<void> {
  if (testInfo.project.name === "mobile") {
    await page.getByLabel("Menu").click();
  }
  await page.getByRole("link", { name: "Settings" }).click();
}

function dateOffset(offsetDays: number): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 10);
}
