# AGENTS.md — PitGPT

> **Keep this file up to date** when adding tools, changing workflows, or
> modifying project structure. This is the canonical reference for agents
> working in this repo.

## Project Overview

PitGPT is a data-only personal clinical trial engine. It ingests research,
runs analysis on protocol + observations, and surfaces results via a CLI,
API, TUI, and web frontend.

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
tests/           # pytest test suite
benchmarks/      # Benchmark fixtures, expected outputs, and saved runs
examples/        # Runnable sample protocol, observations, and document
scripts/         # Helper scripts (mise-env.sh)
bin/             # mise bootstrap script
.github/         # CI workflows
docs/            # Documentation
```

## Tooling

| Tool         | Purpose                        | Config           |
| ------------ | ------------------------------ | ---------------- |
| **uv**       | Python package management      | `pyproject.toml` |
| **mise**     | Tool version management        | `mise.toml`      |
| **hk**       | Git hooks & linting            | `hk.pkl`         |
| **just**     | Task runner                    | `justfile`       |
| **ruff**     | Python linter + formatter      | `pyproject.toml` |
| **mypy**     | Type checking                  | `pyproject.toml` |
| **pytest**   | Testing                        | `pyproject.toml` |
| **actionlint** | GitHub Actions linter        | (builtin)        |
| **zizmor**   | GitHub Actions security linter | (builtin)        |
| **act**      | Local CI runner                | —                |

## Common Commands

```sh
just setup       # Bootstrap mise + install all deps
just test        # Run tests
just lint        # Run non-mutating pre-commit linters via hk
just check       # Run all checks (lint + GHA linting)
just fix         # Auto-fix with ruff via hk (mutates files)
just fmt         # Format with ruff (mutates files)
just typecheck   # Run mypy
just serve       # Start API server
just tui         # Launch TUI
just web-dev     # Start web frontend dev server
just web-build   # Build web frontend for production
just web-install # Install web frontend dependencies
just ci          # Run CI locally with act
just bootstrap   # Regenerate bin/mise bootstrap script
```

## Development Workflow

1. **Setup**: `just setup` (or `./bin/mise install && ./bin/mise exec -- uv sync --python 3.12`)
2. **Code**: Make changes in `src/pitgpt/`
3. **Test**: `just test`
4. **Lint**: `just lint` (runs automatically on commit via hk)
5. **CI**: `just ci` to test GitHub Actions locally

## Conventions

- Python 3.12+, PEP 8, type hints everywhere
- Use `uv run` to execute Python tools (not global installs)
- Use `hk` for linting, not raw ruff/mypy commands
- Ruff config: line length 100, select E/F/I/UP/B/SIM
- Tests live in `tests/`, mirror `src/pitgpt/` structure
- Prefer early returns over nested conditionals
- Keep functions short and focused

## CI

GitHub Actions workflow at `.github/workflows/ci.yml` runs:
- **lint**: `hk run pre-commit --all`
- **check**: `hk run check --all` (includes actionlint + zizmor)
- **test**: `uv run pytest`

Tools are installed via `jdx/mise-action@v4`. Actions are pinned to SHA
hashes per zizmor best practices.

## Environment Variables

- `OPENROUTER_API_KEY` — Required for LLM calls (prompted interactively if missing)
- `PITGPT_DEFAULT_MODEL` — Defaults to `anthropic/claude-sonnet-4`
- `PITGPT_LLM_BASE_URL` — Defaults to `https://openrouter.ai/api/v1`
- `PITGPT_LLM_TIMEOUT_S` — Defaults to `120`
- `PITGPT_LLM_TEMPERATURE` — Defaults to `0`
- `PITGPT_LLM_MAX_TOKENS` — Defaults to `4096`

## Key Documents

- [`docs/prd-v1.md`](docs/prd-v1.md) — Product Requirements Document v1
  (original docx preserved at `docs/prd-v1.docx`)
- [`docs/operator-guide.md`](docs/operator-guide.md) — Local operator workflows
- [`docs/project-purpose.md`](docs/project-purpose.md) — Current prototype purpose
- [`docs/architecture.md`](docs/architecture.md) — Package map and data flow
- [`docs/scope.md`](docs/scope.md) — Current scope and explicit non-scope

## Updating This File

When you make changes that affect any of the above (new tools, new
directories, new commands, changed CI), update this file to match.
