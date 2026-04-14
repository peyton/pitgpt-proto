import { expect, test, type Page, type TestInfo } from "@playwright/test";

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
