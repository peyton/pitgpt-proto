# Implement Claude-Ranked PitGPT Improvements

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

The repo-level `AGENTS.md` asks agents to use an ExecPlan for complex features. The
local plan rules are at `/Users/peyton/.agents/PLANS.md`, and this document follows
those rules.

## Purpose / Big Picture

PitGPT should preserve more of the data users already enter, give each interface the
same validation and export capabilities, and make local operation safer. After this
work, an operator can validate a trial through the CLI or API, use named two-arm
conditions and secondary outcome notes, export or re-import a complete trial bundle,
see progress and adverse-event context in the web and TUI surfaces, optionally protect
the local API with a bearer token, and run a broader benchmark and test set.

The implementation covers Claude Code's 22 suggested improvements, but applies
repository-specific judgment where the repository already has part of the feature. For
example, `pitgpt validate`, Cohen's d, confidence intervals, and result persistence
already exist, so this work enhances and tests them instead of adding duplicates.

## Progress

- [x] (2026-04-14T13:38Z) Created this ExecPlan before editing product code.
- [x] (2026-04-14T14:02Z) Implemented shared Python contracts, validation report service, and analysis fixes.
- [x] (2026-04-14T14:02Z) Added API auth, `/validate`, LLM settings, cache, and Ollama streaming primitives.
- [x] (2026-04-14T14:02Z) Added CLI commands for brief, power, doctor, trial status/export/import/amend, and enhanced validate.
- [x] (2026-04-14T14:02Z) Updated web state/types/pages for condition labels, progress, secondary outcomes, API token, result history, and adverse events.
- [x] (2026-04-14T14:02Z) Updated TUI provider selection and progress display.
- [x] (2026-04-14T14:02Z) Added Tauri notification scheduling primitives and tests.
- [x] (2026-04-14T14:02Z) Expanded tests, docs, and AGENTS command references.
- [x] (2026-04-14T14:09Z) Ran focused verification and the final local gate.

## Surprises & Discoveries

- Observation: Claude's first full repo review exhausted its budget before final output.
  Evidence: the follow-up no-tool `claude -p` run returned a 22-item ranked list.
- Observation: Several Claude suggestions were already partially implemented.
  Evidence: `pitgpt validate`, result Cohen's d and confidence intervals, localStorage
  result persistence, and appointment-brief adverse-event display already exist.
- Observation: The latest available npm notification plugin version is `2.3.3`, not
  `2.10.1`.
  Evidence: `npm view @tauri-apps/plugin-notification version` returned `2.3.3`, and
  installing `^2.10.1` failed with `ETARGET`.

## Decision Log

- Decision: Preserve internal `A` and `B` condition keys while adding user-visible
  condition labels.
  Rationale: The current schedule and analysis code are explicitly two-arm A/B. True
  multi-arm support would require a different randomization and statistical model.
  Date/Author: 2026-04-14 / Codex.
- Decision: Treat secondary outcomes as descriptive summaries that never change the
  primary verdict.
  Rationale: This keeps the primary safety and analysis contract stable while allowing
  users to preserve additional tracked signals.
  Date/Author: 2026-04-14 / Codex.
- Decision: Keep API authentication optional and disabled unless `PITGPT_API_TOKEN` is
  set.
  Rationale: Existing local workflows and browser tests should continue working, while
  self-hosted operators can prevent unauthorized LLM calls.
  Date/Author: 2026-04-14 / Codex.
- Decision: Make LLM caching opt-in and avoid enabling it for normal API ingestion.
  Rationale: Caching is useful for development and benchmarks, but stale safety-policy
  responses are not a safe default.
  Date/Author: 2026-04-14 / Codex.
- Decision: Implement native reminders as Tauri notification permission plus
  deterministic reminder planning and due-reminder delivery while the app is running,
  not as background OS jobs.
  Rationale: Tauri's notification plugin provides permission and delivery primitives;
  background scheduling would be a larger platform-specific subsystem and remains out
  of current prototype scope.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

Implemented the Claude-ranked improvement pass as a cohesive staged change. Python,
TypeScript, and Rust contracts now preserve adherence reasons, adverse-event detail,
secondary outcomes, condition labels, protocol amendments, validation reports, and
trial bundles. CLI and API validation share the same service; API auth is optional
via `PITGPT_API_TOKEN`; LLM metadata headers, document limits, Ollama streaming, and
opt-in cache settings are explicit. The web, TUI, and Tauri surfaces now expose the
new fields and provider/reminder behavior without changing the primary two-arm A/B
analysis contract.

Verification completed:

- `uv run pytest`
- `uv run mypy src/pitgpt`
- `npm --prefix web run test:unit`
- `npm --prefix web run build`
- `cargo test --manifest-path src-tauri/Cargo.toml`
- `cargo clippy --manifest-path src-tauri/Cargo.toml --all-targets -- -D warnings`
- `just bench-analysis`
- `just ci`

## Context and Orientation

PitGPT is a Python package in `src/pitgpt/` with FastAPI in `src/pitgpt/api/`,
Typer CLI in `src/pitgpt/cli/`, Textual TUI in `src/pitgpt/tui/`, deterministic
analysis and ingestion under `src/pitgpt/core/`, React/Vite web code under
`web/src/`, and Tauri Rust commands under `src-tauri/src/`.

The current web `Observation` type already includes `adherence_reason`,
`adverse_event_severity`, and `adverse_event_description`, but the Python model and
CSV parser do not. The CLI already has `pitgpt validate`, and the analysis result
already includes Cohen's d and confidence intervals. The implementation must build
on these existing surfaces.

## Plan of Work

First, update the shared Python data contracts. Extend `Observation`, `Protocol`,
and `ResultCard`; add secondary outcome, protocol amendment, validation report, and
trial bundle models; centralize validation in a new service that both CLI and API use.
Fix the early-stop grade branch while adding branch-complete tests.

Next, update API and LLM operations. Add optional bearer-token protection, implement
`POST /validate`, make LLM referer/title configurable, move document limits into
settings, add opt-in response caching, and add streaming primitives for Ollama.

Then update CLI commands. Enhance `validate`, and add `brief`, `power`, `doctor`,
`trial status`, `trial export`, `trial import`, and `trial amend`. The commands must
be offline-safe unless they explicitly require an LLM.

Then update UI surfaces. In the web app, add progress and block display, result
history selection, API token setting, adverse-event review, secondary outcome fields,
and condition label display. In the TUI, use `list_providers()` instead of hardcoded
models and show analysis progress. In Tauri, add notification scheduling primitives
that can be tested without delivering real OS notifications.

Finally, expand benchmarks and documentation, update this ExecPlan with outcomes, and
run the focused and full verification commands.

## Concrete Steps

Run commands from `/Users/peyton/.codex/worktrees/076a/pitgpt-proto`.

1. Edit source files with `apply_patch`.
2. Add tests beside the existing Python, web, and Rust tests.
3. Run targeted commands after each subsystem, then run:
   `just test`
   `just typecheck`
   `just web-unit`
   `just web-build`
   `just tauri-test`
   `just tauri-lint`
   `just bench-analysis`
   `just ci`

## Validation and Acceptance

Acceptance requires all existing workflows to remain compatible and the new behavior
to be observable. A user should be able to export web CSV with adverse-event fields
and parse it with Python, call `POST /validate`, protect API endpoints with
`PITGPT_API_TOKEN`, generate a trial bundle from the CLI and import it, add protocol
amendments, see trial progress and result history in the web UI, choose providers in
the TUI from detected providers, and run Tauri notification schedule tests without
requiring OS notification permissions.

## Idempotence and Recovery

All edits are source-code changes. Trial bundle import/export commands should be
safe to rerun. LLM cache files must live outside tracked source by default, and any
repo-local cache path introduced for tests must be ignored or created under a
temporary directory.

## Artifacts and Notes

Initial Claude follow-up produced 22 ranked items. The implementer should not blindly
duplicate already-existing features; instead, enhance the existing implementation and
add missing tests.

## Interfaces and Dependencies

Add Python models in `src/pitgpt/core/models.py` and mirror them in
`web/src/lib/types.ts`. Use existing dependencies where possible. If a Tauri
notification plugin dependency is needed, add it deliberately to `src-tauri/Cargo.toml`
and Tauri config, with tests that exercise scheduling logic independently of OS
delivery.

Revision note: Initial ExecPlan created from the user-approved plan before code edits.
