# Flesh Out PitGPT Product Web App And Integration Tests

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

The repo-level `AGENTS.md` asks agents to use an ExecPlan for complex features. The referenced `~/.agent/PLANS.md` was not present on this machine; the equivalent guidance was found at `/Users/peyton/.agents/PLANS.md` and this document follows it.

## Purpose / Big Picture

PitGPT already has a working React shell for creating a personal A/B experiment, reviewing a generated protocol, logging a daily check-in, and viewing results. After this change, a user can start from a question with separate research source text, start from a local v1 template without needing the LLM API, handle restricted or manual-review protocol states, log a current-day or recent backfill observation, see reminder and server status signals, and verify the whole flow with deterministic integration tests.

The behavior is observable by running the web app, starting a template or mocked ingestion flow, locking a protocol, recording observations, stopping early, and seeing a result card with quality and integrity indicators. It is also observable through Playwright browser tests and FastAPI HTTP-boundary tests.

## Progress

- [x] (2026-04-14 05:47Z) Read the supplied implementation plan, current web app, backend API tests, frontend package setup, and ExecPlan guidance.
- [x] (2026-04-14 06:23Z) Created local template definitions and updated the home intake so query text and source documents are tracked separately.
- [x] (2026-04-14 06:23Z) Updated protocol review to support manual review and restricted protocol acknowledgment.
- [x] (2026-04-14 06:23Z) Updated active trial, results, and settings for backfill, reminders, integrity indicators, and server status.
- [x] (2026-04-14 06:23Z) Added Playwright configuration, browser tests, API integration tests, and task runner scripts.
- [x] (2026-04-14 06:23Z) Ran clean verification commands and recorded outcomes.
- [x] (2026-04-14 06:49Z) Fixed repo lint/typecheck blockers found after the main verification pass and reran checks.

## Surprises & Discoveries

- Observation: `~/.agent/PLANS.md` is missing, but `/Users/peyton/.agents/PLANS.md` exists and contains the required ExecPlan format.
  Evidence: `sed -n '1,260p' ~/.agent/PLANS.md` failed with “No such file or directory”; `find ~ -path '*PLANS.md' -maxdepth 4` found `/Users/peyton/.agents/PLANS.md`.
- Observation: The web build fails before `npm ci` only because `web/node_modules` is absent; after installing from `package-lock.json`, `npm run build` succeeds.
  Evidence: `npm ci` added 73 packages, then `npm run build` completed with Vite output under `web/dist`.
- Observation: `npm audit` reports a high-severity Vite dev-server advisory for the current locked Vite version.
  Evidence: `npm audit --json` reports `vite` vulnerable for `<=6.4.1` and `>=6.0.0 <=6.4.1`.
- Observation: Parsing `YYYY-MM-DD` with `new Date(dateStr)` can shift local dates around timezone boundaries and made a one-day backfill appear as two days.
  Evidence: The first Playwright run expected `backfill_days` to be 1 but received 2. The fix parses date inputs as local calendar dates with `new Date(year, month - 1, day)`.
- Observation: On mobile Chromium, keeping the backfill action at the bottom of a long panel made Playwright's user-level click land under preceding controls after scroll.
  Evidence: The first mobile Playwright run timed out because select/textarea elements intercepted clicks intended for `Add Backfill`. Moving the action next to the date input in the panel header fixed the mobile click path.
- Observation: `just lint` originally stashed unstaged work through hk's pre-commit configuration, so it checked the old committed tree instead of the implementation being verified.
  Evidence: The first lint run still reported the pre-fix SciPy and LLM return typing errors after the working tree fix was present. Updating the manual lint recipe to `hk run pre-commit --all --stash none` let it check the current checkout and pass.

## Decision Log

- Decision: Implement the user’s requested plan as an extension of the existing product app rather than creating a marketing page.
  Rationale: The user explicitly selected the product app path in planning, and the current app already matches the PRD workflow.
  Date/Author: 2026-04-14 / Codex.
- Decision: Keep browser tests deterministic by mocking `/api` in Playwright, while adding backend integration tests for the real FastAPI-to-core boundary.
  Rationale: This isolates UI behavior from LLM/network variability but still proves backend contracts.
  Date/Author: 2026-04-14 / Codex.
- Decision: Add client-only local template starts using a new `web/src/lib/templates.ts`.
  Rationale: The PRD requires six v1 templates, and local template starts must not depend on `OPENROUTER_API_KEY`.
  Date/Author: 2026-04-14 / Codex.
- Decision: Use select controls for backfill irritation/adherence while keeping pill buttons for the primary daily check-in.
  Rationale: Backfill is a secondary workflow, and compact selects avoid mobile overlap while preserving the daily check-in's fast tap interface.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

Implemented the requested product-app workflow and test expansion. A user can now attach source material separately from their question, start any of the six local v1 templates without the LLM API, see manual-review and blocked states, acknowledge restricted protocols before locking, log recent backfills, see reminder/API status, and view result integrity metadata.

Verification passed from a clean setup path:

    just setup
    mise all tools are installed
    found 0 vulnerabilities

    just test
    77 passed, 3 warnings in 12.99s

    just web-build
    vite v8.0.8 building client environment for production
    ✓ built

    just web-test
    13 passed, 1 skipped in 4.6s

    cd web && npm audit
    found 0 vulnerabilities

    just lint
    mypy, ruff, formatting, whitespace, merge-conflict, and private-key checks passed

    git diff --check
    no whitespace errors

The remaining warnings are SciPy precision warnings already present in analysis-style tests when values are nearly identical.

## Context and Orientation

The repository is a monorepo. Python app code lives under `pitgpt/`, backend tests live under `tests/`, and the Vite React app lives under `web/`.

The web app uses `web/src/App.tsx` for routes, `web/src/components/Layout.tsx` for the side navigation, and pages under `web/src/pages/`. Shared client state is in `web/src/lib/AppContext.tsx` and is persisted to `localStorage` by `web/src/lib/storage.ts`. API calls are in `web/src/lib/api.ts`, which sends `/api/ingest` and `/api/analyze` through the Vite proxy configured in `web/vite.config.ts`.

An ingestion result is the protocol-generation output returned by `/api/ingest`. A protocol is the locked experiment design, including duration, block length, check-in cadence, washout guidance, and the primary outcome question. An observation is one daily or backfilled check-in row with score, irritation flag, adherence flag, and note. The backend models for these concepts live in `pitgpt/core/models.py` and mirrored TypeScript types live in `web/src/lib/types.ts`.

## Plan of Work

First, add `web/src/lib/templates.ts` with the six v1 templates from the PRD. Each template exports UI metadata and a `templateToIngestionResult` helper that returns an `IngestionResult` with `decision: "generate_protocol"`, a green safety tier, an evidence quality of `novel`, and a protocol matching PRD defaults.

Next, update `web/src/pages/Home.tsx` so the user can enter a question, paste source text, upload a text-like file as a source document, remove sources, submit query plus sources through `ingest(query, documents)`, and start a local template by setting the generated ingestion result directly. The home page keeps the current app identity and avoids medical recommendation copy.

Then update `web/src/pages/ProtocolReview.tsx` so `manual_review_before_protocol` gets a distinct review screen, blocked states stay blocked, yellow or restricted generated protocols require a checkbox acknowledgment before `Lock Protocol & Start`, and concealed schedule display remains unchanged.

Then update `web/src/lib/trial.ts` and `web/src/pages/ActiveTrial.tsx` to support 2-day backfill. Add a helper that builds an observation for an explicit date and marks `is_backfill` plus `backfill_days`. The UI will show a reminder banner when local settings say reminders are enabled and the selected time has already passed today. The trial page will still hide mid-trial comparisons and only show current assignment.

Then update `web/src/pages/Results.tsx` and `web/src/pages/Settings.tsx` with richer integrity/status indicators. Results should show evidence basis, safety tier, adherence, days logged, early stop, and late backfill exclusion. Settings should show API status using `healthCheck` and preserve data export/delete behavior.

Finally, add test tooling. Upgrade Vite tooling, add Playwright, add `playwright.config.ts`, browser tests under `web/tests/e2e/`, API integration tests under `tests/`, and new `just` commands. Keep Playwright tests mocked at `/api` and run them across desktop and mobile projects.

## Concrete Steps

Run commands from `/Users/peyton/.codex/worktrees/9f86/pitgpt-proto` unless a command explicitly changes into `web/`.

1. Edit web app source with `apply_patch`.
2. Run `cd web && npm install --save-dev vite@^8.0.8 @vitejs/plugin-react@^6.0.1 @playwright/test@^1.59.1` so `package.json` and `package-lock.json` update.
3. Run `cd web && npx playwright install chromium` to make browser tests runnable in a clean setup.
4. Run `just test`, `just web-build`, `just web-test`, and `cd web && npm audit`.

Expected successful verification should include all Python tests passing, a Vite production build completing, Playwright tests passing in desktop and mobile projects, and `npm audit` reporting no high-severity Vite advisory.

## Validation and Acceptance

Acceptance is met when:

The home page can submit a query plus at least one pasted or uploaded source document, and the request body contains those source strings in `documents`.

A local template card opens protocol review without calling `/api/ingest`.

A manual-review ingestion response shows a manual review screen and does not allow locking a protocol.

A yellow or restricted protocol cannot be locked until the acknowledgment checkbox is checked.

The active trial screen can submit today’s check-in once, can add a valid 2-day backfill, rejects dates older than 2 days, and marks accepted backfill observations as backfill rows in local storage.

The results page shows quality and integrity metadata in addition to the existing verdict, chart, caveats, and export actions.

The settings page displays API status and persisted reminder settings, while delete data clears local app state.

## Idempotence and Recovery

All implementation steps are source-code edits or package-manager lockfile updates. They are safe to repeat. If Playwright browser installation fails, rerun `cd web && npx playwright install chromium`. If `npm install` changes more packages than expected, inspect `web/package.json` and `web/package-lock.json` before continuing.

Generated folders `web/node_modules/`, `web/dist/`, `.venv/`, and test caches are ignored by `.gitignore`.

## Artifacts and Notes

Baseline evidence before implementation:

    just test
    74 passed, 2 warnings in 28.11s

    cd web && npm run build
    ✓ built in 540ms

    cd web && npm audit --json
    vulnerabilities.vite.severity = "high"

## Interfaces and Dependencies

Add `web/src/lib/templates.ts` exporting:

    export interface TrialTemplate { ... }
    export const trialTemplates: TrialTemplate[]
    export function templateToIngestionResult(template: TrialTemplate): IngestionResult

Extend `web/src/lib/trial.ts` with a date-aware observation builder:

    export function buildObservationForDate(
      trial: Trial,
      dateStr: string,
      score: number,
      irritation: "yes" | "no",
      adherence: "yes" | "no" | "partial",
      note: string,
    ): Observation

Add Playwright dev dependency `@playwright/test` and config at `web/playwright.config.ts`. Keep tests under `web/tests/e2e/` and use route mocking for `/api/ingest`, `/api/analyze`, and `/api/health`.

Revision note: This initial ExecPlan was created before implementation to make the user-supplied plan executable and restartable.

Revision note: Updated after implementation to record completed progress, mobile/date discoveries, final design decisions, and verification output.
