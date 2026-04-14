# Architecture

PitGPT is one Python distribution with a `src/` layout.

```text
src/pitgpt/
  core/         domain models, settings, file parsing, safety policy, LLM, analysis, schedules, templates
  api/          FastAPI wrapper
  cli/          Typer command line interface
  tui/          Textual terminal UI
  benchmarks/   benchmark runner, scoring, and report code
web/            React frontend built with Vite and TypeScript
app/      Tauri v2 native shell, Rust commands, desktop/iOS config
shared/         policy text and template fixtures consumed by Python, Rust, and TypeScript
benchmarks/     benchmark fixture data and expected outputs
examples/       small runnable local inputs
tests/          pytest suite
docs/           operator, product, architecture, and scope docs
```

## Data Flow: Research Ingestion

1. CLI, API, TUI, web, or benchmark code collects a user query and document strings.
2. `pitgpt.core.settings.load_settings` resolves model and API configuration.
3. `pitgpt.core.ingestion.ingest` builds the user message and sends it with
   `pitgpt.core.policy.SAFETY_POLICY_PROMPT`.
4. `pitgpt.core.llm.LLMClient.complete` calls the provider, validates the
   provider response shape, parses JSON, optionally writes/reads the local LLM
   cache, and returns a JSON object.
5. `pitgpt.core.ingestion.ingest` enforces source-size limits, validates the
   object into `IngestionResult`, and attaches policy/model metadata.

Before any provider call, `pitgpt.core.safety.prefilter_query` blocks obvious
RED requests such as medication stopping, prescription-drug comparisons,
supplement/ingestible experiments, urgent symptoms, diagnosis requests, and
invasive-device experiments. After provider output, generated labels,
instructions, and outcome text are checked again so unsafe protocol text cannot
enter a locked trial.

`POST /ingest` defaults to OpenRouter for existing API and web callers. It also
accepts `provider: "ollama"` for local Ollama-backed ingestion. `GET /providers`
returns the stable provider registry:

- `openrouter`
- `ollama`
- `claude_cli`
- `codex_cli`
- `chatgpt_cli`
- `ios_on_device`

Only Ollama is treated as truly offline in this phase. CLI tools are discovered
but may still require account or network access. `ios_on_device` is a reserved
provider kind for later on-device model runtimes.

## Data Flow: Trial Analysis

1. CLI, API, TUI, web, tests, or benchmark code loads an `AnalysisProtocol` and a
   list of `Observation` records.
2. `pitgpt.core.io.parse_observations_csv` centralizes CSV parsing, including
   adherence reasons, adverse-event fields, assigned/actual condition metadata,
   deviation codes, confounders, and secondary outcome score JSON. Strict mode
   rejects unknown columns, duplicate days/dates, and unsorted rows.
3. `pitgpt.core.models` validates two-condition keys, condition labels,
   adherence, backfill flags, adverse-event fields, outcome measures, estimands,
   analysis plans, secondary outcomes, protocol amendments, and 0-10 primary
   scores.
4. `pitgpt.core.analysis.analyze` validates day/date shape, records row-level
   exclusion reasons, filters unusable efficacy rows while retaining safety
   rows, computes paired-period estimates as primary when complete pairs exist,
   keeps Welch daily means as sensitivity, adds randomization p-values,
   equivalence/no-meaningful-difference logic, reliability diagnostics,
   harm-benefit summaries, and returns `ResultCard` with a methods appendix.

`pitgpt.core.validation.validate_trial` returns the shared `ValidationReport`
used by CLI `pitgpt validate` and API `POST /validate`.

## Data Flow: Schedules And Templates

1. `shared/trial_templates.json` defines local no-key trial templates.
2. `pitgpt.core.templates`, `app/src/templates.rs`, and
   `web/src/lib/templates.ts` load that shared fixture.
3. `pitgpt.core.schedule.generate_schedule` turns `duration_weeks`,
   `block_length_days`, and a seed into period assignments.
4. The API, CLI, web frontend, and Tauri commands use the same period shape:
   `period_index`, `pair_index`, `condition`, `start_day`, and `end_day`.

## Native Runtime

The React frontend selects a runtime adapter at startup:

- `web`: calls FastAPI through `/api` and stores state in browser localStorage.
- `tauri-desktop`: invokes Rust commands and stores state in app-local JSON.
- `tauri-ios`: invokes the same offline-safe Rust commands, hides Mac CLI
  discovery, and reserves `ios_on_device` for future model runtimes.

The Tauri command surface is:

```text
get_templates
generate_schedule
plan_trial_reminders
analyze
validate_trial
analyze_example
load_app_state
save_app_state
clear_app_state
export_file
discover_ai_tools
ingest_local
cancel_ingest_local
```

Rust analysis mirrors Python benchmark behavior and uses `statrs` for
Student-t quantiles. Native validation calls `validate_trial` instead of a web
stub, and `just parity-analysis` compares Python and Rust JSON outputs for
golden fields across benchmark fixtures. Native builds do not use a Python
sidecar so the iOS app can run the offline core without a local Python process.

Native reminder scheduling is permission-safe and opt-in. The React app uses
the Tauri notification plugin to request permission only in Tauri runtimes; Rust
plans deterministic reminder days through `plan_trial_reminders` so tests do not
depend on real OS notification delivery.

## Boundaries

`core` owns domain behavior and validation. `api`, `cli`, `tui`, and the React
web frontend should stay thin. `benchmarks` owns evaluation orchestration and
scoring but reads fixture data from the repository root `benchmarks/` directory.

The web frontend uses Vite's dev-server proxy to send `/api/*` requests to the
FastAPI server at `http://localhost:8000`. In local development, run `just serve`
and `just web-dev` in separate terminals. Tauri development runs the same
frontend through `just tauri-dev`.

The repository is monorepo-ready but not split into multiple packages. New apps
or services should import `pitgpt.core` instead of duplicating parsing,
settings, or analysis logic.
