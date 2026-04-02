# PitGPT

Data-only personal clinical trial engine — prototype.

PitGPT ingests biomedical research, runs structured analysis on
self-experiment protocols and observations, and surfaces results through a
CLI, REST API, and terminal UI.

## Quick Start

```sh
# Bootstrap tools and dependencies
just setup

# Or manually:
./bin/mise install   # installs Python, hk, and other tools
uv sync              # installs Python dependencies
```

## Usage

```sh
just serve           # Start the API server (default port 8000)
just tui             # Launch the terminal UI
pitgpt ingest --query "creatine cognition"
pitgpt analyze --protocol protocol.json --observations obs.json
```

## Development

```sh
just test            # Run the test suite
just lint            # Run linters (ruff, mypy) via hk
just check           # Full check including GitHub Actions linting
just fix             # Auto-fix code style
just fmt             # Format with ruff
just typecheck       # Run mypy
```

Git hooks are managed by [hk](https://hk.jdx.dev) — linters run
automatically on commit and push.

## Benchmarks

```sh
just bench                          # Run all benchmarks
just bench model=openai/gpt-4o     # Run with specific model
just bench-report                   # Generate comparison report
```

## CI

GitHub Actions runs lint, check, and test on every push and PR to `master`.
Run CI locally with:

```sh
just ci
```

## Tooling

- [mise](https://mise.jdx.dev) — tool version management (`mise.toml`)
- [uv](https://docs.astral.sh/uv/) — Python package management
- [hk](https://hk.jdx.dev) — git hooks and linting (`hk.pkl`)
- [just](https://just.systems) — task runner (`justfile`)
- [ruff](https://docs.astral.sh/ruff/) — Python linter and formatter
- [mypy](https://mypy.readthedocs.io) — type checker
