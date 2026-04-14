# AGENTS.md — PitGPT

> **Keep this file up to date** when adding tools, changing workflows, or
> modifying project structure. This is the canonical reference for agents
> working in this repo.

## Project Overview

PitGPT is a data-only personal clinical trial engine. It ingests research,
runs analysis on protocol + observations, and surfaces results via a CLI,
API, TUI, web frontend, and Tauri native app.

## Repository Layout

```
src/pitgpt/      # Main Python package
  api/           # FastAPI server
  benchmarks/    # Benchmark runner, scoring, and report code
  cli/           # Typer CLI
  core/          # Ingestion, analysis, LLM integration, models, settings
  tui/           # Textual TUI
web/             # React web frontend (Vite + TypeScript)
  src/           # Components, pages, lib
  public/        # Static assets (logos)
app/       # Tauri v2 Rust native target for macOS and iOS
shared/          # Policy and template fixtures shared across Python/Rust/TypeScript
tests/           # pytest test suite
benchmarks/      # Benchmark fixtures, expected outputs, and saved runs
examples/        # Runnable sample protocol, observations, and document
  bin/             # mise bootstrap script
.github/         # CI workflows and dependency automation config
docs/            # Documentation
```

## Tooling

| Tool         | Purpose                        | Config           |
| ------------ | ------------------------------ | ---------------- |
| **uv**       | Python package management      | `pyproject.toml` |
| **mise**     | Tool version management        | `mise.toml`      |
| **hk**       | Git hooks & linting            | `hk.pkl`         |
| **pkl**      | hk config interpreter          | `mise.toml`      |
| **just**     | Task runner                    | `justfile`       |
| **ruff**     | Python linter + formatter      | `pyproject.toml` |
| **mypy**     | Type checking                  | `pyproject.toml` |
| **pytest**   | Testing                        | `pyproject.toml` |
| **vitest**   | Web unit tests                 | `web/package.json` |
| **playwright** | Web browser tests            | `web/playwright.config.ts` |
| **cargo**    | Tauri Rust build/test/lint      | `app/Cargo.toml` |
| **tauri**    | Native desktop/iOS builds       | `web/package.json` |
| **CocoaPods** | Tauri iOS dependency manager   | `mise.toml`      |
| **actionlint** | GitHub Actions linter        | (builtin)        |
| **zizmor**   | GitHub Actions security linter | (builtin)        |
| **act**      | Local CI runner                | —                |
| **Renovate** | Dependency update PRs          | `renovate.json`  |
| **Dependabot** | Security update PRs          | `.github/dependabot.yml` |

## Common Commands

```sh
just setup       # Bootstrap mise + install all deps
just test        # Run tests
just lint        # Run non-mutating pre-commit linters via hk
just check       # Run all checks (lint + GHA linting)
just audit       # Run uv pip check and npm audit
just doctor      # Check local toolchain and common prerequisites
just fix         # Auto-fix with ruff via hk (mutates files)
just fmt         # Format with ruff (mutates files)
just typecheck   # Run mypy
just bench-analysis # Run deterministic analysis benchmarks
just parity-analysis # Compare Python and Rust deterministic analysis outputs
just bench-ingestion # Run LLM-backed ingestion benchmarks
just bench-all    # Run all benchmark tracks
just serve       # Start API server
just tui         # Launch TUI
pitgpt brief     # Print compact local trial result brief
pitgpt power     # Estimate two-arm sample size for planning
pitgpt doctor    # Check PitGPT CLI/API runtime settings
pitgpt trial status/export/import/amend # Inspect, bundle, restore, or amend trial files
just web-dev     # Start web frontend dev server
just web-build   # Build web frontend for production
just web-unit    # Run Vitest unit tests
just web-test    # Run Playwright browser tests
just web-install # Install web frontend dependencies
just tauri-dev   # Start the macOS Tauri app
just tauri-build # Build the macOS Tauri app
just tauri-test  # Run Rust native tests
just rust-components # Install rustfmt and clippy for the pinned Rust toolchain
just tauri-ios-test # Build the iOS simulator target
just ci          # Run the main local CI gate
just ci-clean    # Bootstrap deps and run the main local CI gate
just clean       # Remove generated build/test artifacts
just release-preflight # Validate Apple signing env vars for release workflows
just bootstrap   # Regenerate bin/mise bootstrap script
```

## Development Workflow

1. **Setup**: `just setup` (or `./bin/mise install && ./bin/mise exec -- uv sync --python 3.12`)
2. **Code**: Make changes in `src/pitgpt/`
3. **Test**: `just test`
4. **Lint**: `just lint` (runs automatically on commit via hk)
5. **Local gate**: run `just ci` for substantive changes, or the narrower
   relevant commands plus `just check` for small, scoped fixes.
6. **GitHub CI**: after pushing, watch the relevant GitHub Actions run to a
   terminal `success` conclusion before handing work back.

## Product Surface Parity

- Treat web frontend feature requests as Tauri native app feature requests too
  unless the user explicitly scopes the work away from native. The macOS/iOS
  Tauri app should not lag the web app when parity is practical.
- Keep the Tauri app offline-capable at all times. Online or cloud-backed modes
  may exist, but they must be optional/toggleable and must not break the local
  offline path.
- When a web feature depends on the API server or hosted services, add the
  matching native/offline behavior or clearly document the blocker and the
  smallest follow-up needed before handing work back.
- Verify Tauri-impacting frontend changes with the relevant Rust/Tauri checks in
  addition to web tests.

## Conventions

- Python 3.12+, PEP 8, type hints everywhere
- Rust 1.94 for Tauri; run through mise-managed `cargo`
- Rust formatting and clippy require toolchain components; `just setup` installs
  them, and `just rust-components` refreshes them if a clean runner lacks them.
- Tauri iOS builds must run `scripts/tauri-ios-npm-shim.sh` after `tauri ios
  init`. The generated Xcode project runs its Rust build phase from
  `app/gen/apple`, and the shim lets that phase resolve the repo's web
  package on clean runners.
- CocoaPods is pinned in `mise.toml`; run it through `./bin/mise exec -- pod`
  rather than assuming a global Homebrew or gem install.
- Use `uv run` to execute Python tools (not global installs)
- Use `hk` for linting, not raw ruff/mypy commands
- Keep every hook and CI runtime CLI declared in `mise.toml`. `hk.pkl`
  requires the `pkl` CLI even before hooks start, so clean runners must install
  it through mise. `just`, `actionlint`, `zizmor`, and `act` are pinned there
  too so local automation does not depend on ad-hoc global versions. CocoaPods
  is also pinned there for iOS Tauri generation and simulator/release builds.
- Ruff config: line length 100, select E/F/I/UP/B/SIM
- Tests live in `tests/`, mirror `src/pitgpt/` structure
- Tauri Rust tests live beside Rust modules in `app/src/`
- Shared safety policy and template data live in `shared/`; keep Python, Rust,
  and TypeScript loaders pointed at those files instead of duplicating fixtures.
- Python analysis is the methodology source of truth. Keep Rust analysis parity
  green with `just parity-analysis` when changing result semantics.
- Prefer early returns over nested conditionals
- Keep functions short and focused

## CI

GitHub Actions workflow at `.github/workflows/ci.yml` uses pinned Ubuntu runner
images, per-job timeouts, and concurrency cancellation for stale PR runs. It runs:
- **lint**: `hk run pre-commit --all`
- **check**: `hk run check --all` (includes actionlint + zizmor)
- **test**: `uv run pytest`
- **web**: npm install, build, Vitest, Playwright, npm audit
- **rust**: cargo fmt, clippy, and cargo test for `app`
- **tauri-macos-build**: signed/notarized macOS artifacts on `master` and manual
  runs when the `apple-signing` environment secrets are configured; otherwise it
  emits a notice and skips artifact creation without failing CI
- **ios-simulator**: Tauri iOS simulator build on PRs and `master` using
  `macos-15` so generated Xcode projects match the available Xcode format; the
  workflow runs the Tauri iOS npm shim after project generation
- **audit**: `uv pip check` and npm audit

`.github/workflows/macos-preview-release.yml` runs on `master` when macOS app
inputs change (`app/`, `web/`, `shared/`, and native build config). It
builds signed macOS DMGs and updates the rolling GitHub prerelease tagged
`macos-preview`. The official release workflow excludes that preview tag.

Release artifacts are built by `.github/workflows/release.yml` when a GitHub
Release is published. That workflow rebuilds signed macOS artifacts and a
signed iOS App Store Connect IPA with a GitHub-run build number, then attaches
them to the release. Shared release preflight, artifact collection, and rolling
preview publishing scripts live in `scripts/apple-release-preflight.sh`,
`scripts/collect-tauri-artifacts.sh`, and `scripts/publish-macos-preview.sh`;
the operator checklist is `docs/release-checklist.md`.

Dependency version updates are handled by Renovate using `renovate.json`.
Renovate automerges minor, patch, digest, and lockfile-maintenance PRs only
through GitHub auto-merge, so required status checks remain the merge gate.
Tauri npm and Cargo packages are grouped together to avoid native build version
skew.
Dependabot scheduled version PRs are disabled in `.github/dependabot.yml` to
avoid duplicate update PRs, but Dependabot security PRs still run for uv, npm,
Cargo, and GitHub Actions. `.github/workflows/dependabot-auto-merge.yml` enables
GitHub auto-merge for same-repo Dependabot patch and minor security PRs without
checking out or executing pull request code.

Tools are installed via `jdx/mise-action@v4`. Actions are pinned to SHA
hashes per zizmor best practices. CI starts from a clean runner, so any tool
needed by `hk.pkl`, hook steps, or workflow commands must be listed in
`mise.toml`. The `check` job runs hk's `zizmor` step through the raw hook
command, so it must export `GITHUB_TOKEN` rather than only `GH_TOKEN`.

## CI Handoff Rule

Do not hand off completed code changes while GitHub CI is failing for the branch
you touched. After pushing a branch or updating `master`, use `gh run list` and
`gh run watch` (or `gh run view --log-failed`) to follow the relevant Actions run
until it succeeds. If CI fails, inspect the failing job logs, fix the underlying
repo or workflow issue, push the fix, and watch the next run. Only hand back with
a failing or unrun GitHub CI state when the blocker is genuinely external, such
as a GitHub outage, unavailable paid macOS runner capacity, or missing production
secrets for a release-only job; include the exact run URL, failing job, and
blocker in the handoff.

For local verification, prefer `just ci` before pushing substantial changes. For
smaller changes, run the narrowest meaningful subset plus `just check`; examples:
Python behavior changes need `just test` and `just typecheck`, web changes need
`just web-build`, `just web-unit`, and relevant Playwright coverage, and Tauri
Rust changes need `just tauri-lint` and `just tauri-test`. GitHub CI remains the
source of truth before handoff.

## Product Safety Direction

PitGPT uses risk-stratified personal experimentation. Low-risk routines that
touch a condition can be allowed when the routine is reversible, non-urgent,
does not change medications or supplements, and helps the user organize
observations for a clinician conversation. Keep doctor language concise and
respectful. Block medication changes, urgent symptoms, diagnosis requests,
invasive interventions, high-risk ingestible changes, and anything that replaces
clinical care.

## Environment Variables

- `OPENROUTER_API_KEY` — Required for LLM calls; set it explicitly when needed
- `PITGPT_API_TOKEN` — Optional bearer token for API endpoints except health/docs
- `PITGPT_DEFAULT_MODEL` — Defaults to `anthropic/claude-sonnet-4`
- `PITGPT_LLM_BASE_URL` — Defaults to `https://openrouter.ai/api/v1`
- `PITGPT_LLM_TIMEOUT_S` — Defaults to `120`
- `PITGPT_LLM_TEMPERATURE` — Defaults to `0`
- `PITGPT_LLM_MAX_TOKENS` — Defaults to `4096`
- `PITGPT_LLM_REFERER` — Optional `HTTP-Referer` header for LLM calls
- `PITGPT_LLM_TITLE` — Optional `X-Title` header for LLM calls
- `PITGPT_MAX_DOCUMENT_CHARS` — Optional per-source character limit; unset by default
- `PITGPT_MAX_TOTAL_DOCUMENT_CHARS` — Optional total source character limit; unset by default
- `PITGPT_LLM_CACHE` — Opt-in deterministic local LLM response cache
- `PITGPT_LLM_CACHE_DIR` — Optional cache directory; default `~/.pitgpt/cache`
- `PITGPT_OLLAMA_BASE_URL` — Defaults to `http://localhost:11434`
- `PITGPT_OLLAMA_MODEL` — Defaults to `llama3.1`

Signing secrets used by native CI/release workflows must live in the
`apple-signing` GitHub environment:

- `APPLE_CERTIFICATE`
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_SIGNING_IDENTITY`
- `APPLE_TEAM_ID`
- `APPLE_API_KEY`
- `APPLE_API_ISSUER`
- `APPLE_API_KEY_P8_B64`
- `APPLE_DEVELOPMENT_TEAM`
- `IOS_PROVISIONING_PROFILE_B64`

Release scripts also honor optional local override paths:

- `APPLE_API_KEY_PATH` — App Store Connect API key output path; defaults to
  `private_keys/AuthKey.p8`
- `IOS_PROVISIONING_PROFILE_DIR` — iOS provisioning profile directory override
- `IOS_PROVISIONING_PROFILE_PATH` — Full iOS provisioning profile output path

## Key Documents

- [`docs/prd-v1.md`](docs/prd-v1.md) — Product Requirements Document v1
  (original docx preserved at `docs/prd-v1.docx`)
- [`docs/operator-guide.md`](docs/operator-guide.md) — Local operator workflows
- [`docs/quickstart.md`](docs/quickstart.md) — Choose CLI, web, TUI, or API path
- [`docs/project-purpose.md`](docs/project-purpose.md) — Current prototype purpose
- [`docs/architecture.md`](docs/architecture.md) — Package map and data flow
- [`docs/scope.md`](docs/scope.md) — Current scope and explicit non-scope

## Updating This File

When you make changes that affect any of the above (new tools, new
directories, new commands, changed CI), update this file to match.
