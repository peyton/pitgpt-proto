# Implement Progressive Disclosure Audit Roadmap

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

The repository does not contain `PLANS.md`; the local execution-plan rules were read from
`/Users/peyton/.agents/PLANS.md`. Maintain this file according to those rules.

## Purpose / Big Picture

PitGPT already runs as a local Python and React prototype, but the audit found several places
where a novice user could be misled or blocked: schedule math ignored protocol block length, the
results headline overstated evidence, local browser state was trusted without validation, and the
web flow exposed too much detail too early. After this change, a user should be able to open the
web app and choose an obvious path: run the example, start from a safe template without an API key,
or ask a research question. Experienced users should still be able to expand raw schedule, protocol,
analysis, and export details.

The work is observable by running the Python tests, building the web app, running Playwright tests,
running analysis benchmarks, and using the web app to start a template, lock a protocol, log a
check-in, stop with a guided confirmation, and view a result with advanced details hidden until
requested.

## Progress

- [x] (2026-04-14 07:03Z) Created this ExecPlan after reading the requested roadmap, repo
  instructions, and current baseline.
- [x] (2026-04-14 07:50Z) Implemented core correctness fixes for schedule generation, result headlines, strict ingestion,
  local state validation, and analysis edge cases.
- [x] (2026-04-14 08:20Z) Implemented progressive disclosure changes in the web intake, protocol review, active trial,
  results, and settings flows.
- [x] (2026-04-14 08:35Z) Added API, CLI, tooling, CI, and documentation improvements that are local-first and do not
  require accounts or server persistence.
- [x] (2026-04-14 08:45Z) Added tests for the new behavior and reran final verification commands.

## Surprises & Discoveries

- Observation: The listed `build-web-apps` skill files for frontend and React guidance are missing
  from the plugin cache in this environment.
  Evidence: `sed` against the listed `SKILL.md` paths returned `No such file or directory`.
- Observation: Vitest's default file discovery picked up Playwright e2e specs.
  Evidence: `just web-unit` first failed because `tests/e2e/app.spec.ts` called
  Playwright's `test.beforeEach`.
  Action: Narrowed the unit-test script to `vitest run src`.

## Decision Log

- Decision: Implement the concrete local-first subset of the 60-item roadmap in this pass.
  Rationale: The roadmap explicitly keeps accounts, server persistence, community sharing, pooled
  results, real email delivery, and push notifications out of scope. The highest-value work is the
  correctness and progressive-disclosure surface that can be verified in this repository.
  Date/Author: 2026-04-14 / Codex.

- Decision: Keep the existing Vite React app and FastAPI backend rather than replacing either.
  Rationale: The repo is already healthy under tests, and the user asked to streamline usability
  rather than rebuild from scratch.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

Implemented the local-first subset of the roadmap: period schedules are generated from
`duration_weeks * 7 / block_length_days`; protocol review displays period ranges; result
headlines no longer invent daily-win percentages; ingestion validates provider protocols
strictly and emits metadata; analysis now reports data-shape warnings, zero-variance CIs, and
paired-period estimates; localStorage is versioned and migrates old schedule state; the web app
has example/template/question paths, collapsed source material, stop/delete modals, import/restore,
advanced result disclosures, seed display, audit hashes, and schedule export; CLI/API/tooling/CI
now expose local template, demo, schedule, validate, audit, and web test surfaces.

Verification completed so far:

    just test
    108 passed

    just web-unit
    3 files passed, 6 tests passed

    just web-build
    built successfully

    just web-test
    13 passed, 1 skipped

    just typecheck
    Success: no issues found in 21 source files

    just check
    ruff-format, ruff, mypy, actionlint, and zizmor passed

    just audit
    uv pip check compatible; npm audit found 0 vulnerabilities

    just doctor
    toolchain checks passed

    just bench-analysis
    8/8 passed, mean score 1.0

## Context and Orientation

PitGPT is a single repository with Python package code under `src/pitgpt`, tests under `tests`,
benchmark fixtures under `benchmarks`, and a Vite React frontend under `web`. The Python core owns
domain models, research ingestion, deterministic analysis, settings, and CSV/JSON parsing. The CLI
in `src/pitgpt/cli/main.py`, FastAPI app in `src/pitgpt/api/main.py`, Textual TUI in
`src/pitgpt/tui/app.py`, and React frontend in `web/src` should stay thin over shared behavior.

A protocol is the locked experiment design: duration, block length, measurement cadence, washout
guidance, and the primary 0-10 outcome question. A schedule is the randomized assignment of
condition A or B to protocol periods. A period is one contiguous interval whose length is
`block_length_days`; this matters because a 14-day block is not the same as a calendar week. An
observation is one daily or backfilled check-in row.

## Plan of Work

First, fix shared correctness. Update web schedule generation so it creates one assignment per
protocol period and balances A/B within period pairs. Add shared schedule helpers for labels and
current-period display. Update result headline copy so it does not derive a daily-win percentage
from sample counts. Harden browser state loading with versioned validation and migration. Make
ingestion validate the provider protocol object strictly instead of substituting silent defaults.
Add analysis guards for duplicate days and zero-variance samples, plus a paired block-level result
as the primary N-of-1 estimate when enough paired blocks exist.

Second, streamline the web app. The home page should expose a simple first-run choice, keep source
material collapsed by default, and show that templates work without an API key. Protocol review
should separate editable labels from locked design details and show hidden periods based on real
block length. Active trial should show days left and next check-in guidance, collapse optional note
and backfill, and replace browser `confirm` and `alert` with accessible inline modal behavior.
Results should present the plain answer first, then hide detailed statistics, block breakdown,
sensitivity analysis, schedule, seed, and raw JSON behind advanced disclosure controls.

Third, add local-first power tools. Add CLI commands for example analysis, protocol/CSV validation,
schedule generation, and observation appending. Add API read endpoints for templates, schedule
generation, and example analysis. Add just recipes for `bench-analysis`, `bench-ingestion`,
`bench-all`, `audit`, and `doctor`, and add web build/e2e/audit coverage to CI.

Finally, update tests and docs. Add Python tests for strict ingestion, analysis validation, schedule
API behavior, and CLI commands. Add frontend unit tests for schedule generation, trial day
calculation, state migration, CSV escaping, and duplicate observation guards. Extend Playwright
tests for the novice paths, collapsed advanced details, stop modal, import/export, and corrupted
localStorage recovery. Update scope and quickstart docs to match current behavior.

## Concrete Steps

All commands should be run from `/Users/peyton/.codex/worktrees/389c/pitgpt-proto`.

1. Edit Python models, analysis, ingestion, API, CLI, and tests with small patches.
2. Edit React state, trial helpers, pages, styles, Playwright tests, and add Vitest tests.
3. Run dependency install only if package scripts or dev dependencies change.
4. Run:
   `just test`
   `just typecheck`
   `just check`
   `just web-build`
   `just web-test`
   `just audit`
   `just bench-analysis`

## Validation and Acceptance

Acceptance requires all listed verification commands to pass. The web app must let a user start a
template without an API key, review real hidden periods, log a check-in, stop through an in-app
confirmation, and view a result whose first sentence does not overstate daily win frequency. The
CLI must expose demo, trial, check-in, and validate commands. The API must expose `/templates`,
`/schedule`, and `/analyze/example`.

## Idempotence and Recovery

The source edits are normal tracked-file changes. Generated folders such as `.venv`, `web/dist`,
`web/node_modules`, and test output are ignored and can be deleted. If web dependencies drift, rerun
`just web-install`. If Playwright browsers are missing, rerun `./bin/mise exec -- npm --prefix web
run test:e2e:install`.

## Artifacts and Notes

Baseline from the audit immediately before implementation:

    just test
    91 passed, 3 warnings

    just typecheck
    Success: no issues found in 19 source files

    just check
    ruff-format, ruff, mypy, actionlint, and zizmor passed

    just web-build
    built successfully after `just web-install`

    just web-test
    13 passed, 1 skipped

    npm --prefix web audit --json
    total vulnerabilities: 0

## Interfaces and Dependencies

Python interfaces to add or update:

- `pitgpt.core.ingestion.ingest(query, documents, client, model_id=None)` should return
  `IngestionResult` with validation metadata.
- `pitgpt.core.analysis.analyze` should return a `ResultCard` that includes a primary analysis
  method and optional paired block estimate.
- `pitgpt.core.schedule` should generate the same period schedule shape used by the web app and
  CLI.
- `pitgpt api` should expose read endpoints for templates, schedule, and example analysis.

Frontend interfaces to add or update:

- `web/src/lib/randomize.ts` should generate schedules by period, not week.
- `web/src/lib/storage.ts` should load a versioned state envelope and migrate older raw state.
- `web/src/lib/types.ts` should use stricter observation and schedule types.
- `web/src/lib/templates.ts` remains the source of built-in local templates for the web app.

Revision note: Initial plan created before implementation to satisfy the repo's ExecPlan
requirement for broad product and architecture changes.
