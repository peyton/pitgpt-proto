# Operator Guide

This guide is for someone running PitGPT locally. It focuses on concrete
commands and expected behavior.

## Setup

Run from the repository root:

```sh
just setup
```

This installs the mise-managed tools and syncs Python dependencies with
Python 3.12 through `uv`. It also installs web frontend dependencies with
Node 22 and Rust 1.94 for the Tauri target. The mise-managed tools include the
hook runtime (`hk` and `pkl`) and GitHub Actions linters used by CI.

If you prefer manual setup:

```sh
./bin/mise install
./bin/mise exec -- uv sync --python 3.12
./bin/mise exec -- npm --prefix web install
```

## Analyze A Completed Trial

Analysis is deterministic and does not use an LLM or require an API key.

```sh
uv run --python 3.12 pitgpt analyze \
  --protocol examples/protocol.json \
  --observations examples/observations.csv \
  --format json
```

Expected behavior:

- Exit code `0`
- JSON output with `quality_grade`, `verdict`, `mean_a`, `mean_b`,
  `difference`, `ci_lower`, `ci_upper`, `analysis_method`, `paired_block`,
  `sensitivity_analyses`, `dataset_snapshot`, `methods_appendix`, `summary`,
  and `caveats`
- No network access

Common failures:

- Missing protocol or observations path: exits with `File not found`
- Invalid protocol JSON: exits with `Invalid input`
- Invalid observation values such as condition `C`, adherence `sometimes`, or
  primary score outside `0` through `10`: exits with `Invalid input`

Shortcut:

```sh
pitgpt demo analyze
```

## Start A Local Trial From Files

Create a template folder:

```sh
pitgpt trial init --template skincare --output-dir my-trial
```

Generate or inspect a deterministic schedule:

```sh
pitgpt trial randomize --protocol my-trial/protocol.json --seed 123
```

Append a daily check-in:

```sh
pitgpt checkin add \
  --observations my-trial/observations.csv \
  --day 1 \
  --date 2026-01-01 \
  --condition A \
  --score 7
```

Validate files before analysis:

```sh
pitgpt validate --protocol my-trial/protocol.json --observations my-trial/observations.csv
```

Strict validation is used by bundle import and catches unknown CSV columns,
duplicate day/date rows, unsorted rows, and invalid typed result/protocol JSON
before writing restored files.

Additional local operators:

```sh
pitgpt brief --protocol my-trial/protocol.json --observations my-trial/observations.csv
pitgpt power --effect 0.5 --sigma 1.5
pitgpt doctor --format json
pitgpt trial status --protocol my-trial/protocol.json --observations my-trial/observations.csv
pitgpt trial export --protocol my-trial/protocol.json --observations my-trial/observations.csv --output my-trial.zip
pitgpt trial import --bundle my-trial.zip --output-dir restored-trial
pitgpt trial amend --protocol my-trial/protocol.json --field warnings --value "Stop if discomfort persists." --reason "Clarified stop criteria before starting."
```

`trial amend` parses JSON values before writing. For example `--value 0.8`
stores a numeric value, while quoted text stays text.

## Run Research Ingestion

Ingestion sends the query and document text to an OpenRouter-compatible model.
It requires `OPENROUTER_API_KEY` unless you explicitly select the local Ollama
provider through the API or Tauri app.

```sh
export OPENROUTER_API_KEY=...
uv run --python 3.12 pitgpt ingest \
  --query "Compare two moisturizers for evening skin comfort" \
  --doc examples/moisturizer-note.md \
  --format json
```

Expected behavior with a valid key:

- Exit code `0`
- JSON output with `decision`, `safety_tier`, `evidence_quality`,
  `evidence_conflict`, `protocol`, `block_reason`, `policy_version`, `model`,
  `source_summaries`, `claimed_outcomes`, and `user_message`

Expected behavior without a key:

```text
OPENROUTER_API_KEY not set
```

The default model is `anthropic/claude-sonnet-4`. Override it with either
`--model` or `PITGPT_DEFAULT_MODEL`.

Local provider discovery:

```sh
curl http://127.0.0.1:8000/providers
```

`openrouter` remains the default. `ollama` uses `PITGPT_OLLAMA_BASE_URL`
(`http://localhost:11434` by default) and `PITGPT_OLLAMA_MODEL`
(`llama3.1` by default). `claude_cli`, `codex_cli`, and `chatgpt_cli` are
discovered as local tools but may require an account or network access.
`ios_on_device` is reserved for later on-device model runtime work.

Optional LLM settings:

- `PITGPT_LLM_REFERER` and `PITGPT_LLM_TITLE` add provider metadata headers.
- `PITGPT_MAX_DOCUMENT_CHARS` and `PITGPT_MAX_TOTAL_DOCUMENT_CHARS` optionally
  restore source-size guards. They are unset by default so full articles and
  large source text can be provided. The CLI `ingest --no-limit` flag bypasses
  configured limits.
- `PITGPT_LLM_CACHE=1` enables deterministic local response caching for
  benchmark/development work. Normal API ingestion leaves caching off by
  default.

## Start The API

```sh
just serve
```

Health check:

```sh
curl http://127.0.0.1:8000/health
```

Expected body:

```json
{"status":"ok"}
```

No-key demo endpoints:

```sh
curl http://127.0.0.1:8000/templates
curl http://127.0.0.1:8000/analyze/example
curl -s http://127.0.0.1:8000/schedule \
  -H 'content-type: application/json' \
  -d '{"duration_weeks":6,"block_length_days":14,"seed":123}'
```

Validate through the API:

```sh
curl -s http://127.0.0.1:8000/validate \
  -H 'content-type: application/json' \
  -d '{"protocol":{"planned_days":14,"block_length_days":7},"observations":[]}'
```

Set `PITGPT_API_TOKEN` to protect non-public API paths. `/health`, `/docs`,
`/redoc`, and `/openapi.json` remain public; other calls need
`Authorization: Bearer <token>`. The web Settings page stores the token locally.

Analyze through the API:

```sh
curl -s http://127.0.0.1:8000/analyze \
  -H 'content-type: application/json' \
  -d '{"protocol":{"planned_days":14,"block_length_days":7},"observations":[{"day_index":1,"date":"2026-01-01","condition":"A","primary_score":7},{"day_index":2,"date":"2026-01-02","condition":"A","primary_score":8},{"day_index":3,"date":"2026-01-03","condition":"B","primary_score":5},{"day_index":4,"date":"2026-01-04","condition":"B","primary_score":6}]}'
```

## Run The TUI

```sh
just tui
```

Use the tabs for ingestion, analysis, and benchmarks. The same API key and
model environment variables apply. The analysis tab has a **Use Example Files**
button for the bundled protocol and observations.

## Run The Web Frontend

Start the API first:

```sh
just serve
```

Start the web frontend in a second terminal:

```sh
just web-dev
```

The Vite dev server proxies `/api` requests to the local FastAPI server.
The first screen supports three paths: run the bundled example, start from a
local template, or ask a question that uses ingestion.

Build the frontend:

```sh
just web-build
```

Run frontend checks:

```sh
just web-unit
just web-test
```

## Run The Tauri macOS App

The Tauri app reuses the React frontend and calls Rust commands for offline
templates, schedules, analysis, local JSON storage, exports, provider
discovery, and Ollama-backed ingestion.

```sh
just tauri-dev
```

Build a macOS app bundle:

```sh
just tauri-build
```

Run native tests:

```sh
just tauri-test
```

Expected behavior without network access:

- Start from a bundled template.
- Lock condition labels and submit check-ins.
- Persist and reload app state from app-local JSON.
- Export JSON, CSV, and appointment brief files.
- Analyze completed observations with deterministic Rust statistics.
- Request native notification permission only when reminders are enabled, then
  plan one reminder per trial day without requiring OS delivery in tests.

Ollama is the only offline AI provider in this phase. If `ollama` is on `PATH`
and `http://localhost:11434/api/tags` returns models, Settings offers those
models first.

## Build The iOS Target

iOS uses the same offline Rust core and React UI, but it does not discover
Mac-installed CLI tools. Settings marks on-device AI as planned. Future work
can attach an implementation to the reserved `ios_on_device` provider.

iOS generation and simulator builds require Xcode and the mise-pinned CocoaPods
tool installed by `just setup`:

```sh
just tauri-ios-test
```

If CocoaPods is missing, Tauri iOS initialization fails before the simulator
build. Run `just setup` to install the pinned `pod` executable through mise.

## Run Benchmarks

Analysis-only benchmarks work without an API key:

```sh
just bench-analysis
```

Python/Rust analysis parity also works without an API key:

```sh
just parity-analysis
```

All benchmarks include LLM ingestion cases and require `OPENROUTER_API_KEY`:

```sh
OPENROUTER_API_KEY=... just bench-all
```

Saved benchmark results are written to `benchmarks/runs/`.

## Audit And Doctor

```sh
just audit
just doctor
```

`just doctor` warns when `OPENROUTER_API_KEY` is missing because only ingestion
requires it. It also prints Rust, Tauri, Xcode, and CocoaPods status for native
builds.
