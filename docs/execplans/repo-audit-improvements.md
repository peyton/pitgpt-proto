# Implement Repo Audit Improvements

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This repository does not contain `PLANS.md`; the local plan rules were found at
`/Users/peyton/.agents/PLANS.md`. Maintain this file according to those rules.

## Purpose / Big Picture

PitGPT is a data-only personal clinical trial prototype. After this change, a new operator
should be able to understand what PitGPT does, what it does not do, run a local analysis from
checked-in example files, inspect the API, and run benchmark checks without guessing paths or
commands. The codebase should stay one installable Python project, but the package should live
under `src/` with clearer boundaries for the core engine, interfaces, and benchmark subsystem.

## Progress

- [x] (2026-04-14 00:00Z) Created this ExecPlan before making implementation changes.
- [x] (2026-04-14 00:10Z) Move the Python package into `src/` and keep import paths stable as `pitgpt.*`.
- [x] (2026-04-14 00:10Z) Move reusable benchmark modules into the installable package while leaving benchmark
  fixtures at the repository root.
- [x] (2026-04-14 00:17Z) Add typed protocol and stricter observation validation.
- [x] (2026-04-14 00:17Z) Centralize CSV parsing, file loading, settings, and safety prompt policy.
- [x] (2026-04-14 00:18Z) Update CLI, API, TUI, and tests for documented command names and stricter contracts.
- [x] (2026-04-14 00:25Z) Add operator-focused docs and runnable examples.
- [x] (2026-04-14 00:31Z) Run and fix `just test`, `just typecheck`, `just check`, CLI examples, benchmark analysis,
  and API health verification.

## Surprises & Discoveries

- Observation: In the audit, bare `uv run` created a `.venv` using Python 3.14.3 even though
  `mise.toml` pins Python 3.12.
  Evidence: `uv run python -c "import sys; print(sys.version)"` printed Python 3.14.3.
- Observation: Typechecking currently fails.
  Evidence: `uv run mypy pitgpt/` reported missing SciPy stubs and an `Any` return from
  `pitgpt/core/llm.py`.
- Observation: The root instruction mentions `~/.agent/PLANS.md`, but that file does not exist.
  Evidence: `/Users/peyton/.agents/PLANS.md` exists and was read instead.
- Observation: Typer exposed `ingest-cmd` and `analyze-cmd` from function names before the CLI
  was renamed.
  Evidence: `uv run --python 3.12 python -m pitgpt.cli.main --help` now lists `ingest`,
  `analyze`, and `benchmark`.
- Observation: Moving observation fields to enums required converting block-breakdown keys to
  string values for mypy.
  Evidence: mypy reported an incompatible tuple assignment until `o.condition.value` was used.
- Observation: `hk` pre-commit stashing made `just lint` check the old tree when the refactor was
  unstaged.
  Evidence: `just lint` initially reported the old `benchmarks.scoring` import after stashing
  current changes. The hook now uses `stash = "none"` and the just recipe passes
  `--stash none --check`.
- Observation: Local `zizmor` fails if `GH_TOKEN` exists but is an empty string.
  Evidence: `just check` initially failed with `invalid value '' for '--github-token'`; the just
  recipe now unsets empty local token variables before running the check hook.

## Decision Log

- Decision: Keep a single Python distribution and implement an incremental monorepo-ready
  structure instead of splitting into multiple packages.
  Rationale: The user selected this direction during planning, and the current codebase is small
  enough that a full workspace split would add friction without immediate payoff.
  Date/Author: 2026-04-14 / Codex.
- Decision: Optimize docs first for end-user operators, with supporting architecture docs for
  engineers and agents.
  Rationale: The user selected operator docs as the primary documentation audience.
  Date/Author: 2026-04-14 / Codex.
- Decision: Keep benchmark fixture data under root `benchmarks/`, but move reusable benchmark
  code into `src/pitgpt/benchmarks/`.
  Rationale: This keeps large fixture data obvious while making code importable from the package
  and avoiding root-level implicit imports.
  Date/Author: 2026-04-14 / Codex.
- Decision: Pin `uv` in `mise.toml` and run just recipes through `./bin/mise exec --`.
  Rationale: The repo already pinned Python and hk through mise, but `uv` was still an undeclared
  global dependency. Running through the repo wrapper makes clean-checkout commands less dependent
  on the user's shell.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

Implemented the 20 repo audit improvements as one cohesive refactor. PitGPT now uses a
`src/pitgpt/` layout, benchmark code lives under `pitgpt.benchmarks`, examples are runnable from a
clean checkout, operator-focused docs explain current behavior and safety boundaries, CLI commands
match the documented names, observation and protocol validation are stricter, shared settings and
I/O helpers remove duplicated parsing, LLM responses are validated before indexing, and local
quality commands are split between non-mutating checks and mutating fix/format recipes.

Verification completed successfully:

    just setup
    Checked 41 packages

    just test
    86 passed, 2 warnings

    just typecheck
    Success: no issues found in 19 source files

    just check
    ruff-format, ruff, mypy, actionlint, and zizmor passed

    just lint
    ruff-format, ruff, mypy, trailing-whitespace, check-merge-conflict, and detect-private-key passed

    uv run python -m pitgpt.cli.main --help
    Listed ingest, analyze, and benchmark

    uv run pitgpt analyze --protocol examples/protocol.json --observations examples/observations.csv --format json
    Returned Grade A JSON result favoring Condition A

    uv run pitgpt benchmark run --track analysis --format json
    8/8 analysis benchmark cases passed with mean_score 1.0

    curl http://127.0.0.1:8000/health
    HTTP 200 with {"status":"ok"}

The remaining warnings are two SciPy runtime precision warnings in tests that intentionally use
nearly identical sample values.

## Context and Orientation

The current repository has application code in `src/pitgpt/`, tests in `tests/`, benchmark
fixtures in `benchmarks/`, documentation in `docs/`, examples in `examples/`, and workflow
commands in `justfile`, `hk.pkl`, `mise.toml`, and `pyproject.toml`. The core package contains
domain models, shared settings and file parsing, LLM-backed research ingestion, and deterministic
analysis. The API, CLI, and TUI are thin interfaces over the core package. Benchmarks evaluate
ingestion cases against expected JSON and analysis cases against expected result cards.

The repository remains one Python project named `pitgpt`. The package implementation now lives
under `src/pitgpt/` so imports come from installed package code instead of the repository root.
Benchmark code is importable as `pitgpt.benchmarks.*`. Fixture data remains in root
`benchmarks/` because it is test data, not runtime package code.

## Plan of Work

First, move the package to `src/pitgpt/`, add Hatchling package configuration, update mypy and
hook paths, and move reusable benchmark modules into `src/pitgpt/benchmarks/`. Then add shared
model types and utility modules: a typed `AnalysisProtocol`, strict observation field validation,
CSV parsing helpers, settings helpers, and a versioned safety policy prompt. Next, update CLI,
API, TUI, benchmarks, and tests to use those shared contracts and to expose the documented CLI
names `ingest` and `analyze`. Finally, add operator-focused docs and examples, run all required
verification commands, and update this ExecPlan with results.

## Concrete Steps

Run all commands from `/Users/peyton/.codex/worktrees/0278/pitgpt-proto`.

1. Move code into `src/pitgpt/` and benchmark modules into `src/pitgpt/benchmarks/`.
2. Update `pyproject.toml`, `justfile`, `hk.pkl`, and `.github/workflows/ci.yml` so commands use
   the package from `src/`, Python 3.12, and non-mutating checks by default.
3. Add or update tests under `tests/` for command names, validation failures, and safety policy.
4. Add `examples/` and docs under `docs/`.
5. Run:
   `just setup`
   `just test`
   `just typecheck`
   `just check`
   `uv run python -m pitgpt.cli.main --help`
   `uv run pitgpt analyze --protocol examples/protocol.json --observations examples/observations.csv --format json`
   `uv run pitgpt benchmark run --track analysis --format json`

## Validation and Acceptance

The work is accepted when tests pass, typecheck passes with zero errors, documented commands match
actual CLI commands, analysis examples run without an API key, ingestion fails clearly without
`OPENROUTER_API_KEY`, and `GET /health` returns HTTP 200 with body `{"status":"ok"}` when the API
server is launched.

## Idempotence and Recovery

The move to `src/` should be done with normal file moves and committed paths, not generated code.
If validation fails after the move, imports should be fixed by updating package configuration or
test imports rather than adding path hacks. Build caches and `.venv` are ignored and can be
deleted safely if interpreter selection drifts.

## Artifacts and Notes

The audit baseline was:

    uv run pytest
    74 passed, 2 warnings

    uv run ruff check .
    All checks passed!

    uv run ruff format --check .
    23 files already formatted

    uv run mypy pitgpt/
    Found 2 errors in 2 files

## Interfaces and Dependencies

`pitgpt.core.models.AnalysisProtocol` must exist and be used by
`pitgpt.core.analysis.analyze`. CLI commands must be available as `pitgpt ingest` and
`pitgpt analyze`. Benchmark functions must be importable from `pitgpt.benchmarks.runner`,
`pitgpt.benchmarks.scoring`, and `pitgpt.benchmarks.report`. Settings must be read through a
shared module rather than directly from environment variables in every interface.
