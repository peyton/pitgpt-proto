# Implement Risk-Stratified Personal Experimentation And Appointment Briefs

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

The repo-level `AGENTS.md` requires an ExecPlan for complex features. The referenced
`~/.agent/PLANS.md` file is not present on this machine; the equivalent rules were read from
`/Users/peyton/.agents/PLANS.md`. This document follows those rules and is self-contained.

## Purpose / Big Picture

PitGPT should help people run structured personal experiments and use the resulting evidence in
better conversations with clinicians. The previous product boundary blocked disease-management
language broadly. After this change, low-risk routines that touch a condition can be allowed when
the routine is reversible, non-urgent, does not change medication or clinical care, and is framed as
self-observation or routine comparison. The app should keep strong hard blocks for medication
changes, acute or crisis symptoms, invasive interventions, diagnosis requests, and high-risk
supplement contexts.

The user-visible outcome is that a condition-adjacent routine can produce a restricted protocol
with concise clinician language, while medication changes remain blocked. A completed result can be
exported as an appointment brief that summarizes the protocol, evidence basis, timeline, adverse
events, uncertainty, and practical questions to bring to a clinician.

## Progress

- [x] (2026-04-14T08:13Z) Read the current repo shape, previous ExecPlans, model/policy/API/web
  files, and verification baseline.
- [x] (2026-04-14T08:13Z) Created this ExecPlan before product code edits.
- [x] (2026-04-14T09:42Z) Updated Python domain models, policy prompt, ingestion parsing, and tests for risk-stratified
  safety metadata.
- [x] (2026-04-14T09:42Z) Updated the React app types, local state migration, trial event/adverse-event capture,
  appointment brief export, and respectful clinician copy.
- [x] (2026-04-14T09:42Z) Fixed clean-checkout web command ergonomics and updated docs.
- [x] (2026-04-14T09:42Z) Ran verification commands and recorded outcomes.

## Surprises & Discoveries

- Observation: The product already has good prototype coverage for local templates, check-ins,
  result cards, backfills, and Playwright flows, so this pass can be additive rather than a rebuild.
  Evidence: `just test` passed 109 tests and `just web-test` passed 13 browser tests after
  `just web-install`.
- Observation: Standalone web commands fail before dependencies are installed.
  Evidence: `just web-unit` initially failed with `vitest: command not found`, and `just web-build`
  initially failed because React and Router packages were not present. Both passed after
  `just web-install`.

## Decision Log

- Decision: Implement a coherent first slice of the 70-item roadmap rather than pretending every
  item can be completed in one pass.
  Rationale: The largest value is changing the safety/product contract and adding doctor-brief
  artifacts while preserving current working flows and tests.
  Date/Author: 2026-04-14 / Codex.
- Decision: Keep medication changes and urgent clinical situations blocked, while allowing low-risk
  condition-adjacent routines only as restricted protocols.
  Rationale: This matches the user's revised direction: trust users, keep clinician language
  minimal, and avoid replacing medical judgment.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

Implemented the first coherent product slice of the revised roadmap. The app now carries a
risk-stratified ingestion contract instead of a blanket disease exclusion, preserves source and
claim metadata, creates protocol and analysis hashes, records trial and adverse-event events in
local web state, and can export a Markdown appointment brief with protocol, sources, observations,
adverse events, uncertainty, and doctor questions.

The implementation intentionally does not complete every item in the 70-line backlog. It establishes
the domain model, prompt contract, UI copy, exports, tests, and command ergonomics needed for the
highest-risk product direction change. Later work can build on this foundation for automated URL/PDF
fetching, source deduplication, literature search, generated OpenAPI types, richer N-of-1 statistics,
calendar/PWA reminders, and registry/community features.

## Context and Orientation

PitGPT is a Python and React monorepo. Python domain code lives under `src/pitgpt/core`, the
FastAPI app lives in `src/pitgpt/api/main.py`, the Typer CLI lives in `src/pitgpt/cli/main.py`, and
the React app lives under `web/src`. The current safety prompt is in `src/pitgpt/core/policy.py`.
The current web intake is `web/src/pages/Home.tsx`, protocol review is
`web/src/pages/ProtocolReview.tsx`, active trial logging is `web/src/pages/ActiveTrial.tsx`, and
results/export UI is `web/src/pages/Results.tsx`.

In this document, "condition-adjacent routine" means a low-risk behavior, environment, tracking
habit, comfort routine, or other reversible routine that may relate to a health condition but does
not ask PitGPT to diagnose, prescribe, change medication, or replace care. "Appointment brief"
means a user-owned Markdown export intended to help a person remember what they tested and what
they want to ask at a visit.

## Plan of Work

First, extend the Python models so an ingestion result can carry `risk_level`,
`risk_rationale`, `clinician_note`, source metadata, extracted claims, and suitability scores.
Revise the safety policy prompt so it no longer blocks all disease language, but instead allows
low-risk condition-adjacent routines with restrictions and concise clinician language. Add tests for
allowed condition-adjacent routines, medication blocks, and copy discipline.

Second, extend frontend types and local trial state. A trial should preserve source metadata,
extracted claims, trial events, adverse events, and protocol/analysis hashes. Observation logging
should still be append-only from the user's perspective, and irritation reports should create
adverse-event records. Results should export CSV/JSON as before and add a Markdown appointment
brief.

Third, update UI copy. Replace broad "disease management is not a fit" language with risk-based
language. Restricted protocols should require acknowledgement without condescending language.
Results should add a short doctor-conversation panel and export action.

Fourth, fix workflow ergonomics by making web commands check for `web/node_modules` and clearly ask
the operator to run `just setup` or `just web-install` when needed.

## Concrete Steps

Run all commands from `/Users/peyton/.codex/worktrees/06ce/pitgpt-proto`.

1. Edit Python files with `apply_patch`: `src/pitgpt/core/models.py`,
   `src/pitgpt/core/policy.py`, `src/pitgpt/core/ingestion.py`, tests under `tests/`, and docs.
2. Edit React files with `apply_patch`: `web/src/lib/types.ts`, `web/src/lib/trial.ts`,
   `web/src/lib/storage.ts`, `web/src/lib/templates.ts`, `web/src/pages/Home.tsx`,
   `web/src/pages/ProtocolReview.tsx`, `web/src/pages/ActiveTrial.tsx`,
   `web/src/pages/Results.tsx`, and frontend tests.
3. Edit `justfile` so web commands run a lightweight dependency guard.
4. Run the verification commands listed below.

## Validation and Acceptance

Acceptance requires these commands to pass:

    just test
    just check
    just web-unit
    just web-build
    just web-test
    just bench-analysis

Behavior acceptance is met when tests prove that a low-risk condition-adjacent routine can be
generated with restrictions, a medication timing change is blocked, the UI copy uses concise
clinician language, and the results page can export an appointment brief containing protocol,
result, adverse events, source notes, timeline, uncertainty, and questions.

## Idempotence and Recovery

All changes are tracked source edits and are safe to repeat. Generated folders such as `.venv`,
`web/node_modules`, `web/dist`, `web/test-results`, and `benchmarks/runs` are ignored and can be
deleted. If web verification fails because dependencies are missing, run `just web-install` and
repeat the command.

## Artifacts and Notes

Baseline before implementation:

    just test
    109 passed

    just web-unit
    failed before dependency install with: sh: vitest: command not found

    just web-build
    failed before dependency install because React and Router type packages were absent

    just web-install
    found 0 vulnerabilities

    just web-unit
    3 passed, 6 tests passed

    just web-build
    built successfully

    just web-test
    13 passed, 1 skipped

    just bench-analysis
    8/8 passed, mean score 1.0

    just check
    ruff, ruff-format, mypy, actionlint, and zizmor passed

After implementation:

    just test
    116 passed

    just check
    ruff, ruff-format, mypy, actionlint, and zizmor passed

    just web-unit
    4 passed, 9 tests passed

    just web-build
    built successfully

    just web-test
    13 passed, 1 skipped

    just bench-analysis
    8/8 passed, mean score 1.0

## Interfaces and Dependencies

Python model additions should be additive defaults so old fixture JSON remains valid:

    class RiskLevel(StrEnum): LOW, CONDITION_ADJACENT_LOW, MODERATE, HIGH, CLINICIAN_REVIEW
    class ResearchSource(BaseModel): ...
    class ExtractedClaim(BaseModel): ...
    class SuitabilityScore(BaseModel): ...

`IngestionResult` should expose these optional fields with default empty values:
`risk_level`, `risk_rationale`, `clinician_note`, `sources`, `extracted_claims`,
`suitability_scores`, and `next_steps`.

Frontend trial additions should also be additive:

    interface TrialEvent { id, type, timestamp, detail }
    interface AdverseEvent { id, date, day_index, condition, description, severity }
    interface Trial { protocolHash, analysisPlanHash, events, adverseEvents, ... }

The appointment brief export should be a pure TypeScript helper that returns Markdown so it can be
unit-tested without a browser download.

Revision note: Initial ExecPlan created to make the user's revised roadmap executable in a focused
first implementation pass.
