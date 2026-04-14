# PitGPT

PitGPT is a data-only personal clinical trial engine prototype. It turns a
question plus optional research notes into a structured personal A/B experiment,
then analyzes completed observations with deterministic statistics.

PitGPT is not a doctor, diagnosis tool, medication planner, or product ranking
engine. The current prototype is built for low-risk personal experiments and
safety-gated research ingestion. Low-risk routines that touch a condition can be
framed when they are reversible, non-urgent, and do not change medications or
replace care, with concise language for bringing the plan or result to a
clinician.

## What You Can Run

- `pitgpt analyze`: analyze a completed A/B trial from a protocol JSON file and
  observations CSV file. This does not require an API key.
- `pitgpt demo analyze`: analyze the bundled example trial without an API key.
- `pitgpt trial init`: create protocol, schedule, and observations templates.
- `pitgpt trial randomize`: generate a deterministic period schedule.
- `pitgpt checkin add`: append one observation row with duplicate guards.
- `pitgpt validate`: validate protocol and observation files before analysis.
- `pitgpt brief`: print a compact result brief for a local trial.
- `pitgpt power`: estimate two-arm sample size for planning.
- `pitgpt doctor`: inspect local PitGPT runtime configuration.
- `pitgpt trial status/export/import/amend`: inspect, bundle, restore, and
  record amendments for local trial files.
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
- `just tauri-dev`: launch the macOS Tauri app using the React UI.
- `just tauri-build`: build the macOS Tauri app bundle.
- `just tauri-test`: run Rust tests for native commands, storage, providers, and analysis.
- `just tauri-ios-test`: build the iOS simulator target used by CI.
- `just audit` and `just doctor`: check dependency health and local prerequisites.
- `just ci-clean`: bootstrap dependencies and run the main local CI gate.
- `just release-preflight`: verify Apple signing environment variables before release.

## Setup

Use Python 3.12, Node 22, and Rust 1.94. The repository pins the toolchain with
`mise.toml` and `.python-version`; the `just` recipes run tools through
`./bin/mise exec --`.
The mise config is the source of truth for local and CI tools, including `hk`,
`pkl`, `just`, `actionlint`, and `zizmor`.

```sh
just setup
```

Manual setup is:

```sh
./bin/mise install
./bin/mise exec -- rustup component add rustfmt clippy
./bin/mise exec -- uv sync --python 3.12
./bin/mise exec -- npm --prefix web ci
```

## Choose Your Path

- Web novice path: `just serve` plus `just web-dev`, then choose **Run example**
  or **Start template**.
- Native macOS path: `just tauri-dev`, then use templates, check-ins, exports,
  analysis, or Ollama-backed local ingestion.
- iOS simulator path: install Xcode and CocoaPods, then run `just tauri-ios-test`.
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
- `PITGPT_API_TOKEN`: optional bearer token for API endpoints except health/docs
- `PITGPT_LLM_BASE_URL`: defaults to `https://openrouter.ai/api/v1`
- `PITGPT_LLM_TIMEOUT_S`: defaults to `120`
- `PITGPT_LLM_TEMPERATURE`: defaults to `0`
- `PITGPT_LLM_MAX_TOKENS`: defaults to `4096`
- `PITGPT_LLM_REFERER`: optional `HTTP-Referer` header for LLM calls
- `PITGPT_LLM_TITLE`: optional `X-Title` header for LLM calls
- `PITGPT_MAX_DOCUMENT_CHARS`: defaults to `12000`
- `PITGPT_MAX_TOTAL_DOCUMENT_CHARS`: defaults to `40000`
- `PITGPT_LLM_CACHE`: set to `1`/`true` for deterministic local LLM caching
- `PITGPT_LLM_CACHE_DIR`: optional cache directory, defaulting to `~/.pitgpt/cache`
- `PITGPT_OLLAMA_BASE_URL`: defaults to `http://localhost:11434`
- `PITGPT_OLLAMA_MODEL`: defaults to `llama3.1`

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

When `PITGPT_API_TOKEN` is set, send `Authorization: Bearer <token>` to API
endpoints other than `/health`, `/docs`, `/redoc`, and `/openapi.json`.
`POST /validate` shares the CLI validation contract and returns a structured
validation report without running analysis.

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

## Native Desktop And iOS

The Tauri v2 app lives in `src-tauri/` and reuses the Vite React UI. Web mode
continues to call FastAPI through `/api`; native mode routes templates,
schedules, analysis, storage, export, local ingestion, and AI discovery through
Rust commands. Tauri storage is app-local JSON, so the native app can function
offline without a Python sidecar. Daily reminders can opt into native
notification permission; reminder planning is deterministic and does not require
real OS notification delivery in tests.

Run the macOS app:

```sh
just tauri-dev
```

Build the macOS app:

```sh
just tauri-build
```

Run native Rust tests:

```sh
just tauri-test
```

Ollama is the offline provider in this phase. The app discovers Ollama models
from `http://localhost:11434/api/tags`; it also detects `claude`, `codex`, and
`chatgpt` CLIs and labels them as local tools that may need an account or
network access. The `ios_on_device` provider is reserved for future on-device
model runtime work and is not selectable yet.

iOS currently supports the offline app core: templates, local JSON storage,
trial tracking, schedule generation, exports, and deterministic analysis. It
does not discover Mac-installed CLIs. iOS Tauri generation/builds require Xcode
and CocoaPods. The `just` recipes run `scripts/tauri-ios-npm-shim.sh` after
Tauri project generation so Xcode can find the repo's web package from the
generated `src-tauri/gen/apple` project:

```sh
just tauri-ios-test
```

GitHub CI skips signed macOS artifact creation when Apple signing secrets are
not configured. Release builds require Apple signing secrets in the
`apple-signing` GitHub environment for signed/notarized macOS builds and signed
iOS App Store Connect IPAs:
`APPLE_CERTIFICATE`, `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGNING_IDENTITY`,
`APPLE_TEAM_ID`, `APPLE_API_KEY`, `APPLE_API_ISSUER`,
`APPLE_API_KEY_P8_B64`, `APPLE_DEVELOPMENT_TEAM`, and
`IOS_PROVISIONING_PROFILE_B64`.
See `docs/release-checklist.md` for the release preflight commands, secret
definitions, build-number behavior, and current Mac App Store gaps.

On `master`, changes to the native app inputs (`src-tauri/`, `web/`, `shared/`,
or native build config) also update the rolling GitHub prerelease tagged
`macos-preview` with the latest signed macOS DMG.

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
just tauri-test  # Rust native tests
just tauri-build # macOS Tauri bundle
just rust-components # install rustfmt + clippy for the pinned Rust toolchain
just ci          # main local CI gate
just ci-clean    # bootstrap dependencies and run the main local CI gate
just clean       # remove generated build and test artifacts
just release-preflight # validate Apple release signing environment
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

Before handing off code changes, run `just ci` for substantive work or the
smallest relevant local gate plus `just check` for narrow fixes. After pushing,
watch the matching GitHub Actions run until it reaches `success`; if it fails,
use the job logs as the next task and keep fixing unless the blocker is external.

## More Docs

- `docs/operator-guide.md`: step-by-step user workflows
- `docs/quickstart.md`: choose CLI, web, TUI, or API path
- `docs/release-checklist.md`: Apple signing and release workflow checklist
- `docs/project-purpose.md`: current purpose and safety contract
- `docs/architecture.md`: module map and data flow
- `docs/scope.md`: prototype scope versus PRD and post-MVP ideas
- `docs/prd-v1.md`: broader product requirements draft
