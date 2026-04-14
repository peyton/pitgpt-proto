# PitGPT

PitGPT is a data-only personal clinical trial engine prototype. It turns a
question plus optional research notes into a structured personal A/B experiment,
then analyzes completed observations with deterministic statistics.

PitGPT is not a doctor, diagnosis tool, treatment recommender, symptom tracker,
or product ranking engine. The current prototype is built for low-risk personal
experiments and safety-gated research ingestion.

## What You Can Run

- `pitgpt analyze`: analyze a completed A/B trial from a protocol JSON file and
  observations CSV file. This does not require an API key.
- `pitgpt ingest`: send a question and optional documents to the research
  ingestion engine. This requires `OPENROUTER_API_KEY`.
- `pitgpt benchmark run`: run the benchmark suite against deterministic analysis
  cases and, when an API key is present, LLM ingestion cases.
- `pitgpt benchmark report`: compare saved benchmark runs.
- `just serve`: start the FastAPI wrapper.
- `just tui`: launch the terminal UI.

## Setup

Use Python 3.12. The repository pins the toolchain with `mise.toml` and
`.python-version`, and `uv` commands are run with `--python 3.12`.

```sh
just setup
```

Manual setup is:

```sh
./bin/mise install
uv sync --python 3.12
```

## Analyze The Example Trial

This path works without network access or an API key:

```sh
uv run --python 3.12 pitgpt analyze \
  --protocol examples/protocol.json \
  --observations examples/observations.csv \
  --format json
```

Expected result: JSON containing a `quality_grade`, `mean_a`, `mean_b`,
`difference`, confidence interval fields, and plain-language caveats.

## Run Research Ingestion

Ingestion calls an OpenRouter-compatible chat completion API and validates the
model response into PitGPT's structured result model.

```sh
export OPENROUTER_API_KEY=...
uv run --python 3.12 pitgpt ingest \
  --query "Compare two moisturizers for evening skin comfort" \
  --doc examples/moisturizer-note.md \
  --format json
```

If `OPENROUTER_API_KEY` is missing, ingestion exits with
`OPENROUTER_API_KEY not set`.

Optional configuration:

- `PITGPT_DEFAULT_MODEL`: defaults to `anthropic/claude-sonnet-4`
- `PITGPT_LLM_BASE_URL`: defaults to `https://openrouter.ai/api/v1`
- `PITGPT_LLM_TIMEOUT_S`: defaults to `120`
- `PITGPT_LLM_TEMPERATURE`: defaults to `0`
- `PITGPT_LLM_MAX_TOKENS`: defaults to `4096`

## API And TUI

Start the API:

```sh
just serve
```

Then check health:

```sh
curl http://127.0.0.1:8000/health
```

The expected body is:

```json
{"status":"ok"}
```

Launch the terminal UI:

```sh
just tui
```

## Benchmarks

Run deterministic analysis cases:

```sh
uv run --python 3.12 pitgpt benchmark run --track analysis --format json
```

Run all benchmark cases, including LLM ingestion cases:

```sh
OPENROUTER_API_KEY=... just bench
```

Saved runs are written to `benchmarks/runs/`, which is ignored by git.

## Development

```sh
just test        # pytest
just lint        # non-mutating pre-commit checks
just typecheck   # mypy on src/pitgpt
just check       # lint + GitHub Actions checks
just fix         # mutating ruff fixes through hk
just fmt         # mutating ruff format and fix
```

Application code lives in `src/pitgpt/`. Benchmark fixture data lives in
`benchmarks/`. Runnable example inputs live in `examples/`.

## More Docs

- `docs/operator-guide.md`: step-by-step user workflows
- `docs/project-purpose.md`: current purpose and safety contract
- `docs/architecture.md`: module map and data flow
- `docs/scope.md`: prototype scope versus PRD and post-MVP ideas
- `docs/prd-v1.md`: broader product requirements draft
