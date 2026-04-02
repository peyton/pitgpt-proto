default:
    @just --list

# Bootstrap mise and install all tools + dependencies
setup:
    ./bin/mise install
    uv sync

# Install Python dependencies
install:
    uv sync

# Run the test suite
test *args:
    uv run pytest {{args}}

# Run linters via hk (pre-commit checks)
lint:
    hk run pre-commit --all

# Run all checks (lint + GHA linting)
check:
    hk run check --all

# Auto-fix code with ruff
fix:
    hk run fix --all

# Format code with ruff
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# Type-check
typecheck:
    uv run mypy pitgpt/

# Start the API server
serve port="8000":
    uv run uvicorn pitgpt.api.main:app --host 0.0.0.0 --port {{port}} --reload

# Launch the TUI
tui:
    uv run python -m pitgpt.tui.app

# Run benchmarks
bench model="" track="all" cases="":
    #!/usr/bin/env bash
    args=""
    if [ -n "{{model}}" ]; then args="$args --model {{model}}"; fi
    if [ "{{track}}" != "all" ]; then args="$args --track {{track}}"; fi
    if [ -n "{{cases}}" ]; then args="$args --cases {{cases}}"; fi
    uv run pitgpt benchmark run $args

# Generate benchmark comparison report
bench-report output="":
    #!/usr/bin/env bash
    args=""
    if [ -n "{{output}}" ]; then args="$args --output {{output}}"; fi
    uv run pitgpt benchmark report $args

# Run a single ingestion query
ingest query model="":
    #!/usr/bin/env bash
    args="--query '{{query}}'"
    if [ -n "{{model}}" ]; then args="$args --model {{model}}"; fi
    uv run pitgpt ingest $args

# Run analysis on protocol + observations
analyze protocol observations:
    uv run pitgpt analyze --protocol {{protocol}} --observations {{observations}}

# Run CI checks locally via act
ci:
    act -j ci

# Regenerate bin/mise bootstrap script
bootstrap:
    mise generate bootstrap --write ./bin/mise
