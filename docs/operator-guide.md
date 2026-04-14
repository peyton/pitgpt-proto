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
Node 22. The mise-managed tools include the hook runtime (`hk` and `pkl`) and
GitHub Actions linters used by CI.

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
  `difference`, `ci_lower`, `ci_upper`, `summary`, and `caveats`
- No network access

Common failures:

- Missing protocol or observations path: exits with `File not found`
- Invalid protocol JSON: exits with `Invalid input`
- Invalid observation values such as condition `C`, adherence `sometimes`, or
  primary score outside `0` through `10`: exits with `Invalid input`

## Run Research Ingestion

Ingestion sends the query and document text to an OpenRouter-compatible model.
It requires `OPENROUTER_API_KEY`.

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
  `evidence_conflict`, `protocol`, `block_reason`, and `user_message`

Expected behavior without a key:

```text
OPENROUTER_API_KEY not set
```

The default model is `anthropic/claude-sonnet-4`. Override it with either
`--model` or `PITGPT_DEFAULT_MODEL`.

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
model environment variables apply.

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

Build the frontend:

```sh
just web-build
```

## Run Benchmarks

Analysis-only benchmarks work without an API key:

```sh
uv run --python 3.12 pitgpt benchmark run --track analysis --format json
```

All benchmarks include LLM ingestion cases and require `OPENROUTER_API_KEY`:

```sh
OPENROUTER_API_KEY=... uv run --python 3.12 pitgpt benchmark run --format json
```

Saved benchmark results are written to `benchmarks/runs/`.
