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
- `pitgpt demo analyze`: analyze the bundled example trial without an API key.
- `pitgpt trial init`: create protocol, schedule, and observations templates.
- `pitgpt trial randomize`: generate a deterministic period schedule.
- `pitgpt checkin add`: append one observation row with duplicate guards.
- `pitgpt validate`: validate protocol and observation files before analysis.
- `pitgpt ingest`: send a question and optional documents to the research
  ingestion engine. This requires `OPENROUTER_API_KEY`.
- `pitgpt benchmark run`: run the benchmark suite against deterministic analysis
  cases and, when an API key is present, LLM ingestion cases.
- `pitgpt benchmark report`: compare saved benchmark runs.
- `just serve`: start the FastAPI wrapper.
- `just tui`: launch the terminal UI.
- `just web-dev`: launch the React web frontend.
- `just web-build`: build the React web frontend.
- `just web-unit` and `just web-test`: run frontend unit and browser tests.
- `just audit` and `just doctor`: check dependency health and local prerequisites.

## Setup

Use Python 3.12 and Node 22. The repository pins the toolchain with
`mise.toml` and `.python-version`; the `just` recipes run tools through
`./bin/mise exec --`.
The mise config is the source of truth for local and CI tools, including `hk`,
`pkl`, `actionlint`, and `zizmor`.

```sh
just setup
```

Manual setup is:

```sh
./bin/mise install
./bin/mise exec -- uv sync --python 3.12
./bin/mise exec -- npm --prefix web install
```

## Choose Your Path

- Web novice path: `just serve` plus `just web-dev`, then choose **Run example**
  or **Start template**.
- CLI no-key path: `pitgpt demo analyze` or `pitgpt trial init`.
- API demo path: `GET /templates`, `POST /schedule`, and `GET /analyze/example`.
- Research ingestion path: set `OPENROUTER_API_KEY`, then use `pitgpt ingest` or
  the web question flow.

See `docs/quickstart.md` for exact commands.

## Analyze The Example Trial

This path works without network access or an API key:

```sh
uv run --python 3.12 pitgpt analyze \
  --protocol examples/protocol.json \
  --observations examples/observations.csv \
  --format json
```

Or use the shorter demo command:

```sh
uv run --python 3.12 pitgpt demo analyze --format json
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

## API, TUI, And Web

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

Launch the web frontend in a second terminal after starting the API:

```sh
just web-dev
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`.
Build the frontend with:

```sh
just web-build
```

## Benchmarks

Run deterministic analysis cases:

```sh
just bench-analysis
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
just web-unit    # Vitest unit tests
just web-test    # Playwright browser tests
just audit       # uv pip check + npm audit
just doctor      # toolchain and prerequisite checks
just fix         # mutating ruff fixes through hk
just fmt         # mutating ruff format and fix
```

Application code lives in `src/pitgpt/`. Web frontend code lives in `web/`.
Benchmark fixture data lives in `benchmarks/`. Runnable example inputs live in
`examples/`.

When adding or changing hook and CI tools, declare them in `mise.toml`. GitHub
Actions installs only the mise-managed toolchain on a clean runner, and `hk.pkl`
requires the `pkl` CLI before any hook step can run. CI's raw `hk run check`
command also needs `GITHUB_TOKEN` for the `zizmor` step.

## More Docs

- `docs/operator-guide.md`: step-by-step user workflows
- `docs/quickstart.md`: choose CLI, web, TUI, or API path
- `docs/project-purpose.md`: current purpose and safety contract
- `docs/architecture.md`: module map and data flow
- `docs/scope.md`: prototype scope versus PRD and post-MVP ideas
- `docs/prd-v1.md`: broader product requirements draft
