default:
    @just --list

mise := "./bin/mise exec --"
python := "3.12"
uv_run := "./bin/mise exec -- uv run --python " + python
uv_sync := "./bin/mise exec -- uv sync --python " + python

# Bootstrap mise and install all tools + dependencies
setup:
    ./bin/mise install
    {{mise}} just rust-components
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
    just tauri-lint

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

# Compare Python and Rust deterministic analysis outputs
parity-analysis:
    {{uv_run}} python -m scripts.parity_analysis

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

# List shared MedGemma workflows
workflow-list:
    {{uv_run}} pitgpt workflow list

# Run one workflow demo payload
workflow-demo workflow model="" provider="":
    #!/usr/bin/env bash
    args="--workflow {{workflow}}"
    if [ -n "{{model}}" ]; then args="$args --model {{model}}"; fi
    if [ -n "{{provider}}" ]; then args="$args --provider {{provider}}"; fi
    ./bin/mise exec -- uv run --python 3.12 pitgpt workflow demo $args

# Run all workflow demo payloads
workflow-demo-all model="" provider="":
    #!/usr/bin/env bash
    args=""
    if [ -n "{{model}}" ]; then args="$args --model {{model}}"; fi
    if [ -n "{{provider}}" ]; then args="$args --provider {{provider}}"; fi
    ./bin/mise exec -- uv run --python 3.12 pitgpt workflow demo-all $args

# Run analysis on protocol + observations
analyze protocol observations:
    {{uv_run}} pitgpt analyze --protocol {{protocol}} --observations {{observations}}

# Install Rust components needed by the Tauri lint checks
rust-components:
    {{mise}} rustup component add rustfmt clippy

# Run the main CI checks locally without requiring Docker or GitHub-hosted macOS runners
ci:
    {{mise}} just lint
    {{mise}} just check
    {{mise}} just test
    {{mise}} just web-build
    {{mise}} just web-unit
    {{mise}} just web-test
    {{mise}} just tauri-test
    {{mise}} just audit

# Bootstrap dependencies, then run the main local CI gate
ci-clean:
    {{mise}} just setup
    {{mise}} just ci

# Remove generated build and test artifacts
clean:
    rm -rf .mypy_cache .pytest_cache .ruff_cache
    find . -type d -name __pycache__ -prune -exec rm -rf {} +
    rm -rf benchmarks/runs web/dist web/test-results web/playwright-report
    rm -rf app/target app/gen/apple app/gen/ios app/gen/schemas

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
    ./bin/mise exec -- just --version
    ./bin/mise exec -- pkl --version
    ./bin/mise exec -- npm --prefix web --version
    test -d web/node_modules || (echo "web/node_modules missing; run just setup or just web-install" >&2; exit 1)
    ./bin/mise exec -- cargo --version
    ./bin/mise exec -- rustup component list --installed | grep -E '^(rustfmt|clippy)-'
    ./bin/mise exec -- npm --prefix web run tauri -- --version
    if command -v xcodebuild >/dev/null 2>&1; then
      xcodebuild -version | sed -n '1p'
    else
      echo "xcodebuild is not available; iOS builds require Xcode"
    fi
    if ./bin/mise exec -- pod --version >/dev/null 2>&1; then
      ./bin/mise exec -- pod --version
    else
      echo "CocoaPods is not available; run just setup before running iOS Tauri init/build"
    fi
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

_ios-deps:
    #!/usr/bin/env bash
    set -euo pipefail
    command -v xcodebuild >/dev/null 2>&1 || (echo "xcodebuild missing; install Xcode before running iOS builds" >&2; exit 1)
    ./bin/mise exec -- pod --version >/dev/null 2>&1 || (echo "CocoaPods missing; run just setup before running iOS Tauri init/build" >&2; exit 1)

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

# Run Rust formatting and clippy checks for the Tauri target
tauri-lint:
    {{mise}} cargo fmt --manifest-path app/Cargo.toml -- --check
    {{mise}} cargo clippy --manifest-path app/Cargo.toml --all-targets -- -D warnings

# Run Rust unit/integration tests for the Tauri target
tauri-test:
    {{mise}} cargo test --manifest-path app/Cargo.toml --all-targets

# Start the macOS Tauri app
tauri-dev: _web-deps
    {{mise}} npm --prefix web run tauri:dev

# Build the macOS Tauri app
tauri-build: _web-deps
    {{mise}} npm --prefix web run tauri:build

# Start the iOS Tauri app on a simulator
tauri-ios-dev: _web-deps _ios-deps
    if [ ! -d app/gen/apple ]; then ./bin/mise exec -- npm --prefix web run tauri -- ios init --ci; fi
    scripts/tauri-ios-npm-shim.sh
    {{mise}} npm --prefix web run tauri:ios:dev

# Build the iOS Tauri app
tauri-ios-build: _web-deps _ios-deps
    if [ ! -d app/gen/apple ]; then ./bin/mise exec -- npm --prefix web run tauri -- ios init --ci; fi
    scripts/tauri-ios-npm-shim.sh
    {{mise}} npm --prefix web run tauri:ios:build

# Run the iOS simulator build path used by CI.
tauri-ios-test: _web-deps _ios-deps
    #!/usr/bin/env bash
    set -euo pipefail
    if [ ! -d app/gen/apple ]; then
      ./bin/mise exec -- npm --prefix web run tauri -- ios init --ci
    fi
    scripts/tauri-ios-npm-shim.sh
    ./bin/mise exec -- npm --prefix web run tauri -- ios build --debug --target aarch64-sim --ci

# Validate macOS release signing environment without writing secret files
release-preflight-macos:
    scripts/apple-release-preflight.sh macos-dmg

# Validate iOS App Store release signing environment without writing secret files
release-preflight-ios:
    scripts/apple-release-preflight.sh ios-appstore

# Validate both Apple release signing environments
release-preflight:
    {{mise}} just release-preflight-macos
    {{mise}} just release-preflight-ios

# Regenerate bin/mise bootstrap script
bootstrap:
    mise generate bootstrap --write ./bin/mise
