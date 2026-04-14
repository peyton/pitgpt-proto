# Architecture

PitGPT is one Python distribution with a `src/` layout.

```text
src/pitgpt/
  core/         domain models, settings, file parsing, safety policy, LLM, analysis
  api/          FastAPI wrapper
  cli/          Typer command line interface
  tui/          Textual terminal UI
  benchmarks/   benchmark runner, scoring, and report code
benchmarks/     benchmark fixture data and expected outputs
examples/       small runnable local inputs
tests/          pytest suite
docs/           operator, product, architecture, and scope docs
```

## Data Flow: Research Ingestion

1. CLI, API, TUI, or benchmark code collects a user query and document strings.
2. `pitgpt.core.settings.load_settings` resolves model and API configuration.
3. `pitgpt.core.ingestion.ingest` builds the user message and sends it with
   `pitgpt.core.policy.SAFETY_POLICY_PROMPT`.
4. `pitgpt.core.llm.LLMClient.complete` calls the provider, validates the
   provider response shape, parses JSON, and returns a JSON object.
5. `pitgpt.core.ingestion.ingest` validates the object into `IngestionResult`.

## Data Flow: Trial Analysis

1. CLI, API, TUI, tests, or benchmark code loads an `AnalysisProtocol` and a
   list of `Observation` records.
2. `pitgpt.core.io.parse_observations_csv` centralizes CSV parsing.
3. `pitgpt.core.models` validates conditions, adherence, backfill flags, and
   0-10 primary scores.
4. `pitgpt.core.analysis.analyze` filters unusable rows, computes Welch
   two-sample statistics, grades data quality, and returns `ResultCard`.

## Boundaries

`core` owns domain behavior and validation. `api`, `cli`, and `tui` should stay
thin. `benchmarks` owns evaluation orchestration and scoring but reads fixture
data from the repository root `benchmarks/` directory.

The repository is monorepo-ready but not split into multiple packages. New apps
or services should import `pitgpt.core` instead of duplicating parsing,
settings, or analysis logic.
