# Implement Rock-Solid Methodology Contracts

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

The repo-level `AGENTS.md` requires an ExecPlan for complex features. The local plan rules are
at `/Users/peyton/.agents/PLANS.md`, and this document follows those rules.

## Purpose / Big Picture

PitGPT already lets a user run a structured two-condition personal trial, but the current prototype
does not make the statistical question, locked analysis plan, data exclusions, safety handling, and
reproducibility metadata first-class enough for publishable personal insight. After this change, a
completed result should explain exactly what was estimated, which data were used or excluded, why
the result is actionable or not, and how another operator can reproduce it from the exported files.

The first implementation tranche intentionally prioritizes deterministic, locally verifiable
methodology over heavier modeling. Bayesian probabilities, autocorrelation models, and generated
cross-language schemas remain staged until simulations and golden parity tests are in place.

## Progress

- [x] (2026-04-14T18:17Z) Created this ExecPlan before product-code edits.
- [x] (2026-04-14T18:46Z) Added first-class methodology, lock, dataset,
  interpretation, and methods appendix models in Python.
- [x] (2026-04-14T19:05Z) Refactored Python analysis so paired period estimates
  are primary when complete paired blocks exist, with Welch retained as
  sensitivity.
- [x] (2026-04-14T19:23Z) Added deterministic RED prefilter, generated-protocol
  safety checks, stricter CSV/bundle validation, and typed amendments.
- [x] (2026-04-14T20:57Z) Mirrored core methodology/result fields in TypeScript
  and Rust.
- [x] (2026-04-14T21:12Z) Added native validation parity and
  `just parity-analysis` for Python/Rust golden output comparisons.
- [x] (2026-04-14T21:25Z) Added focused Python, Rust, web-unit, and Playwright
  coverage plus docs updates.
- [x] (2026-04-14T21:33Z) Ran final verification commands and updated this
  plan with evidence.

## Surprises & Discoveries

- Observation: Claude Code was installed but unavailable for the requested review because its local
  CLI quota was exhausted.
  Evidence: `claude -p ...` returned `You've hit your limit · resets 11am (America/Los_Angeles)`.
- Observation: The fallback read-only reviewer confirmed that `ResultCard.analysis_method` can say
  `paired_blocks` while `difference`, `ci_lower`, `ci_upper`, `verdict`, and `summary` still come
  from unpaired daily Welch-style estimates.
  Evidence: `src/pitgpt/core/analysis.py` computes Welch values before block estimates and stores
  those Welch values in the top-level result.

## Decision Log

- Decision: Implement a deterministic first tranche rather than adding Bayesian or autocorrelation
  models immediately.
  Rationale: Bayesian benefit probabilities and autocorrelation-aware uncertainty are valuable, but
  they can overstate certainty unless calibrated by simulation. The safer first step is to lock the
  estimand, make paired-period inference primary, expose randomization and sensitivity outputs, and
  add simulations/benchmarks before richer model claims.
  Date/Author: 2026-04-14 / Codex.
- Decision: Keep existing low-level file analysis commands usable, but add stronger integrity
  metadata and validation around trial-style outputs.
  Rationale: Operators already use `pitgpt analyze` on local files. It should remain useful, while
  active-trial completion and exported results become more reproducible and explicit.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

First tranche implemented. The core methodological contract is now present in
Python, TypeScript, and Rust; paired-period estimates drive top-level results
when complete pairs exist; RED safety checks can block before LLM calls; and
completed results export a methods appendix with canonical SHA-256 hashes.
Deferred work remains for generated JSON Schema contracts, broader pathological
fixtures beyond the current deterministic cases, Bayesian/autocorrelation
models, and server-enforced no-mid-trial reveal.

## Context and Orientation

PitGPT is a monorepo-style prototype. Python domain models live in `src/pitgpt/core/models.py`;
analysis lives in `src/pitgpt/core/analysis.py`; research ingestion lives in
`src/pitgpt/core/ingestion.py`; CSV and JSON loading live in `src/pitgpt/core/io.py`; shared
validation lives in `src/pitgpt/core/validation.py`; the CLI is in `src/pitgpt/cli/main.py`; the
FastAPI app is in `src/pitgpt/api/main.py`; React types and trial helpers live under `web/src/lib`;
and native Rust mirrors live under `app/src`.

An estimand is the precise question the analysis answers: which outcome is compared, which
conditions are contrasted, what summary measure is used, how missed adherence or early stopping is
handled, and what difference counts as meaningful. A methods appendix is an exportable record of
the estimand, analysis method, input hashes, exclusions, deviations, sensitivity analyses, and
software versions needed to reproduce or review the result.

## Plan of Work

First add Python model contracts for the methodology layer. The new models should include an
outcome measure with direction and anchors, a primary estimand, an analysis plan with method version
and intercurrent-event strategies, trial locks with canonical SHA-256 hashes, row-level dataset
snapshots, sensitivity analysis results, actionability classes, and methods appendices. Existing
fields must remain backwards compatible so fixture protocols still validate.

Next refactor Python analysis. The analysis should continue computing daily mean summaries, but
when at least two complete A/B period pairs exist, the top-level difference, confidence interval,
verdict, and summary should use the paired-period estimate. Welch daily means should move into a
structured sensitivity result. Add randomization-inference p-values for paired signs, equivalence
classification using the directional minimum meaningful difference, row exclusion reasons,
missing-data bounds, reliability warnings, carryover and time-trend warnings, harm-benefit counts,
and a methods appendix.

Then harden input and safety. Add a deterministic safety prefilter for obvious RED/YELLOW boundary
queries before LLM calls; validate generated protocol labels and user-editable labels against
blocked medication, supplement, disease-treatment, urgent, and invasive-device framing; make CSV
parsing optionally strict; validate bundle imports before writing output files; and preserve typed
values in `pitgpt trial amend`.

Then mirror the contracts. Update TypeScript result and trial types, web trial hashing to use
canonical SHA-256, and the Rust models/results to preserve the new JSON shape. Implement native
validation parity instead of returning a success stub in Tauri runtime.

Finally add tests and docs. Extend Python tests for methodology contracts and safety hardening,
Rust tests for result fields, web tests for hashing and validation behavior, a parity script plus
`just parity-analysis`, pathological benchmark fixtures, and docs updates in `AGENTS.md`,
`docs/architecture.md`, `docs/scope.md`, and `docs/operator-guide.md`.

## Concrete Steps

Run commands from `/Users/peyton/.codex/worktrees/aaf7/pitgpt-proto`.

1. Edit files with `apply_patch`.
2. Run focused Python tests after core analysis changes: `just test tests/test_analysis.py`.
3. Run broader Python checks: `just test` and `just typecheck`.
4. If web dependencies are missing, run `just web-install`, then `just web-unit` and `just web-build`.
5. Run native checks: `just tauri-test` and `just tauri-lint`.
6. Run methodology benchmark checks: `just bench-analysis` and `just parity-analysis`.
7. Run `just check` before handoff if time and environment allow.

## Validation and Acceptance

Acceptance for this first tranche requires the following observable behavior:

- `ResultCard.analysis_method` and top-level estimate fields agree. If paired period analysis is
  primary, `difference`, `ci_lower`, `ci_upper`, `verdict`, and `summary` all reflect paired periods.
- Result JSON includes method version, estimand, actionability class, sensitivity analyses,
  dataset snapshot, row exclusion reasons, reliability warnings, and methods appendix metadata.
- Obvious RED ingestion requests are blocked before an LLM call.
- Unsafe generated or edited labels are rejected with specific messages.
- Strict CSV and bundle import validation catch duplicate days/dates and invalid schedule-condition
  mappings without silently writing bad trial files.
- Python and Rust analysis outputs match for declared golden fields across benchmark fixtures.

## Idempotence and Recovery

The implementation is source-only. Generated caches, virtual environments, web build outputs, and
benchmark runs are ignored. If strict validation breaks an old fixture, migrate the fixture through
the versioned loader instead of weakening validation globally. If Rust parity lags Python for a new
field, preserve the JSON field with a conservative default and add a test documenting the gap.

## Artifacts and Notes

Baseline immediately before implementation:

    just test
    141 passed in 35.08s

    just typecheck
    Success: no issues found in 24 source files

    just web-unit
    web/node_modules missing; run just setup or just web-install

Verification during implementation:

    just test
    149 passed

    just typecheck
    Success: no issues found

    just web-install
    npm ci completed with 0 vulnerabilities

    just web-unit
    22 passed

    just web-build
    completed successfully

    just web-test
    21 passed, 1 skipped

    just tauri-test
    15 passed

    just tauri-lint
    cargo fmt --check and clippy passed

    just parity-analysis
    Python/Rust analysis parity passed for 9 case(s)

    just check
    ruff-format, ruff, mypy, actionlint, zizmor, cargo fmt, and clippy passed

    just audit
    uv pip check passed; npm audit found 0 vulnerabilities

## Interfaces and Dependencies

Do not add heavy statistical dependencies in the first tranche. Use existing SciPy in Python and
existing `statrs` in Rust. Use Pydantic models for Python contracts, TypeScript interfaces for the
web, and Serde structs/enums for Rust.

New or updated Python interfaces:

- `pitgpt.core.models.PrimaryEstimand`
- `pitgpt.core.models.AnalysisPlan`
- `pitgpt.core.models.TrialLock`
- `pitgpt.core.models.OutcomeMeasure`
- `pitgpt.core.models.SensitivityAnalysisResult`
- `pitgpt.core.models.AnalysisDatasetSnapshot`
- `pitgpt.core.models.MethodsAppendix`
- `pitgpt.core.analysis.analyze`
- `pitgpt.core.ingestion.prefilter_query`
- `pitgpt.core.validation.validate_trial`
- `pitgpt.core.io.parse_observations_csv(..., strict=True)`

New or updated commands:

- `pitgpt trial amend` must preserve JSON-typed values.
- `just parity-analysis` must compare Python and Rust analysis outputs for golden fields.

Revision note: Initial ExecPlan created as the first tracked mutation for the user-requested
rock-solid methodology upgrade.
