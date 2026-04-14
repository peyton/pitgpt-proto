default:
    @just --list

mise := "./bin/mise exec --"
uv_run := "./bin/mise exec -- uv run --python 3.12"
uv_sync := "./bin/mise exec -- uv sync --python 3.12"

# Bootstrap mise and install all tools + dependencies
setup:
    ./bin/mise install
    {{uv_sync}}
    {{mise}} npm --prefix web ci
    {{mise}} npm --prefix web run test:e2e:install

# Install Python dependencies
install:
    {{uv_sync}}

# Run the test suite
test *args:
    {{uv_run}} pytest {{args}}

# Run non-mutating linters via hk
lint:
    {{mise}} hk run pre-commit --all --check --stash none

# Run all checks (lint + GHA linting)
check:
    env -u GH_TOKEN -u GITHUB_TOKEN {{mise}} hk run check --all --check

# Auto-fix code with ruff
fix:
    {{mise}} hk run fix --all --fix

# Format code with ruff
fmt:
    {{uv_run}} ruff format .
    {{uv_run}} ruff check --fix .

# Type-check
typecheck:
    {{uv_run}} mypy src/pitgpt/

# Start the API server
serve port="8000":
    {{uv_run}} uvicorn pitgpt.api.main:app --host 0.0.0.0 --port {{port}} --reload

# Launch the TUI
tui:
    {{uv_run}} python -m pitgpt.tui.app

# Run benchmarks
bench model="" track="all" cases="":
    #!/usr/bin/env bash
    args=""
    if [ -n "{{model}}" ]; then args="$args --model {{model}}"; fi
    if [ "{{track}}" != "all" ]; then args="$args --track {{track}}"; fi
    if [ -n "{{cases}}" ]; then args="$args --cases {{cases}}"; fi
    ./bin/mise exec -- uv run --python 3.12 pitgpt benchmark run $args

# Run deterministic analysis benchmarks
bench-analysis:
    {{uv_run}} pitgpt benchmark run --track analysis

# Run ingestion benchmarks through the configured LLM provider
bench-ingestion model="":
    #!/usr/bin/env bash
    args="--track ingestion"
    if [ -n "{{model}}" ]; then args="$args --model {{model}}"; fi
    ./bin/mise exec -- uv run --python 3.12 pitgpt benchmark run $args

# Run all benchmark tracks
bench-all model="":
    #!/usr/bin/env bash
    args=""
    if [ -n "{{model}}" ]; then args="$args --model {{model}}"; fi
    ./bin/mise exec -- uv run --python 3.12 pitgpt benchmark run $args

# Generate benchmark comparison report
bench-report output="":
    #!/usr/bin/env bash
    args=""
    if [ -n "{{output}}" ]; then args="$args --output {{output}}"; fi
    ./bin/mise exec -- uv run --python 3.12 pitgpt benchmark report $args

# Run a single ingestion query
ingest query model="":
    #!/usr/bin/env bash
    args="--query '{{query}}'"
    if [ -n "{{model}}" ]; then args="$args --model {{model}}"; fi
    ./bin/mise exec -- uv run --python 3.12 pitgpt ingest $args

# Run analysis on protocol + observations
analyze protocol observations:
    {{uv_run}} pitgpt analyze --protocol {{protocol}} --observations {{observations}}

# Run CI checks locally via act
ci:
    {{mise}} act -j ci

# Audit Python environment and web dependencies
audit:
    {{mise}} uv pip check --python 3.12
    {{mise}} npm --prefix web audit

# Check local toolchain and common prerequisites
doctor:
    #!/usr/bin/env bash
    set -euo pipefail
    ./bin/mise exec -- python --version
    ./bin/mise exec -- uv --version
    ./bin/mise exec -- npm --prefix web --version
    test -d web/node_modules || (echo "web/node_modules missing; run just web-install" >&2; exit 1)
    if [ -z "${OPENROUTER_API_KEY:-}" ]; then
      echo "OPENROUTER_API_KEY is not set; ingest and ingestion benchmarks will be unavailable"
    else
      echo "OPENROUTER_API_KEY is set"
    fi

# Install web frontend dependencies
web-install:
    {{mise}} npm --prefix web ci

_web-deps:
    #!/usr/bin/env bash
    test -d web/node_modules || (echo "web/node_modules missing; run just setup or just web-install" >&2; exit 1)

# Start web frontend dev server
web-dev: _web-deps
    {{mise}} npm --prefix web run dev

# Build web frontend for production
web-build: _web-deps
    {{mise}} npm --prefix web run build

# Run web unit tests
web-unit: _web-deps
    {{mise}} npm --prefix web run test:unit

# Run web browser integration tests
web-test: _web-deps
    {{mise}} npm --prefix web run test:e2e

# Regenerate bin/mise bootstrap script
bootstrap:
    mise generate bootstrap --write ./bin/mise
