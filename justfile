default:
    @just --list

mise := "./bin/mise exec --"
uv_run := "./bin/mise exec -- uv run --python 3.12"
uv_sync := "./bin/mise exec -- uv sync --python 3.12"

# Bootstrap mise and install all tools + dependencies
setup:
    ./bin/mise install
    {{uv_sync}}

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

# Regenerate bin/mise bootstrap script
bootstrap:
    mise generate bootstrap --write ./bin/mise
