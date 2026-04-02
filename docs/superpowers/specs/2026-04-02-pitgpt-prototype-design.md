# PitGPT Prototype Design Spec

## Goal

Build a data-only prototype of PitGPT — a personal clinical trial machine for motivated self-experimenters. The prototype tests whether the core data pipeline (research ingestion + protocol synthesis + statistical analysis) produces compelling outputs across multiple LLM providers before investing in a full product build.

## Architecture

Monorepo with shared core library. Four consumer packages import core directly.

```
pitgpt-proto/
  pitgpt/
    core/         # domain models, LLM client, ingestion pipeline, stats engine
    api/          # FastAPI HTTP wrapper
    cli/          # typer CLI
    tui/          # textual TUI
  benchmarks/     # runner, scoring, fixtures, expected outputs
  tests/          # pytest suite
```

## Core Library (`pitgpt/core/`)

### models.py

Pydantic v2 models for the entire domain:

- `SafetyTier` — GREEN / YELLOW / RED enum
- `EvidenceQuality` — novel / weak / moderate / strong enum
- `IngestionDecision` — generate_protocol / generate_protocol_with_restrictions / manual_review_before_protocol / block enum
- `Protocol` — template, duration_weeks, block_length_days, cadence, washout, primary_outcome_question, screening, warnings
- `IngestionResult` — decision, safety_tier, evidence_quality, evidence_conflict, protocol (optional), block_reason (optional), user_message
- `Observation` — day_index, date, condition, primary_score, irritation, adherence, note, is_backfill, backfill_days
- `QualityGrade` — A / B / C / D enum
- `ResultCard` — quality_grade, mean_a, mean_b, difference, ci_lower, ci_upper, n_used_a, n_used_b, adherence_rate, days_logged_pct, early_stop, summary, caveats

### llm.py

OpenRouter-compatible LLM client:

- `LLMClient(model, api_key, base_url="https://openrouter.ai/api/v1")`
- `async complete(system: str, user: str) -> dict` — returns parsed JSON
- Uses httpx async client
- Retries with exponential backoff (3 attempts)
- Configurable temperature (default 0.0 for determinism)

### ingestion.py

- `async ingest(query: str, documents: list[str], client: LLMClient) -> IngestionResult`
- System prompt encodes full PRD safety framework (Green/Yellow/Red), entity extraction, evidence quality tagging, protocol synthesis rules, and copy guidelines
- Sends query + document contents as user message
- Requests structured JSON matching IngestionResult schema
- Validates response with Pydantic

### analysis.py

Deterministic statistical engine, no LLM:

- `analyze(protocol: dict, observations: list[Observation]) -> ResultCard`
- Filtering rules:
  - Exclude rows where adherence = "no"
  - Include rows where adherence = "partial"
  - Treat rows where is_backfill = yes AND backfill_days > 2 as missing
- Welch's two-sample t-test (scipy.stats.ttest_ind with equal_var=False)
- Quality grading:
  - A: adherence >= 85%, days_logged >= 90%, full protocol completed
  - B: adherence >= 70%, days_logged >= 75%, full protocol completed
  - C: otherwise usable but limited, or early stop
  - D: adherence < 50% or days_logged < 50%
- Early stop: compute on executed days, cap grade at C
- Plain-language summary generation (template-based, no LLM)

## API Layer (`pitgpt/api/`)

FastAPI app with three endpoints:

- `POST /ingest` — body: `{query, documents[], model}` → `IngestionResult`
- `POST /analyze` — body: `{protocol, observations[]}` → `ResultCard`
- `GET /health` → `{status: "ok"}`

No auth. Model selection per-request.

## CLI (`pitgpt/cli/`)

Typer app. Commands:

- `pitgpt ingest --query "..." [--doc file ...] --model MODEL [--format json|table|pretty]`
- `pitgpt analyze --protocol FILE --observations FILE [--format json|table|pretty]`
- `pitgpt benchmark run [--model MODEL] [--track ingestion|analysis|all] [--cases CASE,...] [--format json|table|pretty]`
- `pitgpt benchmark report [--output FILE]`

Default format: pretty (TTY) or json (pipe).

## TUI (`pitgpt/tui/`)

Textual app with three screens:

- **Ingest** — query input, document file paths, model selector, result panel
- **Analyze** — protocol/observations file inputs, result card display
- **Benchmark** — model selector, track filter, live progress table, summary

## Benchmarks (`benchmarks/`)

### Structure

```
benchmarks/
  fixtures/            # source documents (md, pdf.txt)
  analysis_fixtures/   # protocol JSON + observation CSV per case
  expected_outputs/    # reference JSON per case
  cases.jsonl          # case definitions
  runner.py            # orchestration
  scoring.py           # comparison logic
  report.py            # cross-run aggregation
  runs/                # saved run results (gitignored)
```

### Scoring — Track A (Ingestion)

Per-case scores (all binary except protocol_similarity):
- decision_match, safety_tier_match, evidence_quality_match, evidence_conflict_match, template_match
- protocol_similarity (0-1 float): normalized distance across duration, block_length, cadence, washout

### Scoring — Track B (Analysis)

Per-case scores:
- grade_match (binary)
- difference_accuracy (0-1, 1.0 - min(1.0, |actual - expected| / |expected|))
- ci_accuracy (0-1, average of lower and upper bound accuracy)
- early_stop_match (binary)

### Run Storage

Each run saved as `benchmarks/runs/{timestamp}_{model_slug}.json` with full per-case results. Report command compares across runs.

## Tooling

- **mise.toml** — Python 3.12, OPENROUTER_API_KEY env var
- **hk.toml** — ruff format, ruff check, mypy
- **pyproject.toml** — uv project with all dependencies
- **justfile** — install, test, lint, fmt, serve, tui, bench, bench-report

## Dependencies

Runtime: pydantic, httpx, fastapi, uvicorn, typer, textual, scipy
Dev: pytest, pytest-asyncio, ruff, mypy, respx (HTTP mocking)

## Tests

- `test_models.py` — model validation, serialization round-trips
- `test_analysis.py` — all 8 RES cases from benchmark, exact match against expected outputs
- `test_ingestion.py` — mock LLM responses, validate parsing and error handling
- `test_api.py` — FastAPI test client, endpoint contracts
- `test_cli.py` — CLI invocation via typer.testing.CliRunner
- `test_scoring.py` — scoring functions against known inputs

## What This Prototype Answers

1. Can an LLM reliably classify safety tiers (Green/Yellow/Red) for the PRD's boundary cases?
2. Can an LLM extract entities and synthesize valid protocols from diverse document types?
3. Does the deterministic analysis engine produce correct statistical results?
4. Which models (Claude, GPT-4o, Gemini, Llama, etc.) perform best on ingestion tasks?
5. Is the data model sufficient to represent the full trial lifecycle?
6. Is the protocol synthesis prompt robust enough, or does it need retrieval/fine-tuning?
