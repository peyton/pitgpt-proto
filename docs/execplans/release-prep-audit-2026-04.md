# Release-prep audit and improvement pass

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This repository follows the local ExecPlan rules in `~/.agents/PLANS.md`. The file is not checked into the repository, so this plan includes the necessary release-prep context directly.

## Purpose / Big Picture

PitGPT is preparing for a release. After this work, a maintainer should have a cleaner, more reliable release candidate with at least fifty concrete improvements or fixes across code, tests, documentation, scripts, and configuration. The result must be observable by running the repository's standard commands from the project root, especially the narrower checks that protect Python behavior, web behavior, Tauri behavior, and release automation.

## Progress

- [x] (2026-04-14T18:01:53Z) Read repository instructions and the local ExecPlan requirements.
- [x] (2026-04-14T18:01:53Z) Created this release-prep ExecPlan in `docs/execplans/release-prep-audit-2026-04.md`.
- [x] (2026-04-14T18:06:00Z) Ran baseline Python, web, lint/check, audit, Tauri, and doctor checks; only `just doctor` initially failed from an opaque clean-checkout Tauri CLI ordering problem.
- [x] (2026-04-14T18:18:00Z) Implemented 91 concrete release-prep improvements and recorded them in `docs/release-audit-2026-04.md`.
- [x] (2026-04-14T18:24:00Z) Repaired regressions found during verification: a Rust MSRV clippy issue, a Playwright backfill expectation that conflicted with stricter trial bounds, and an actionlint shellcheck hang in the macOS preview workflow.
- [x] (2026-04-14T18:27:24Z) Ran final verification gates and recorded the exact commands and outcomes.

## Surprises & Discoveries

- Observation: `just doctor` failed on a clean checkout after creating the Python virtualenv because the recipe tried `npm --prefix web exec tauri -- --version` before checking `web/node_modules`.
  Evidence: The baseline command ended with `npm error could not determine executable to run` instead of the intended "web/node_modules missing" guidance.
- Observation: `actionlint` 1.7.12 with shellcheck integration hung on the long inline shell block in `.github/workflows/macos-preview-release.yml`.
  Evidence: `just check` stalled for more than two minutes with an `actionlint .github/workflows/macos-preview-release.yml` process; `actionlint -shellcheck= .github/workflows/macos-preview-release.yml` exited immediately. Extracting the release logic into `scripts/publish-macos-preview.sh` made actionlint pass normally.
- Observation: Tightening web backfill validation exposed that the existing Playwright test backfilled yesterday immediately after creating a trial today.
  Evidence: `just web-test` failed waiting for "Backfill saved." until the test aged the trial start date before exercising a valid missed check-in.

## Decision Log

- Decision: Treat this as a broad release-prep stabilization pass rather than a single feature.
  Rationale: The user asked to audit everything and make at least fifty improvements and fixes. That requires touching multiple release surfaces and maintaining a restartable plan.
  Date/Author: 2026-04-14 / Codex
- Decision: Keep the pass focused on release hardening rather than new product capabilities.
  Rationale: The highest-release-risk issues were validation, state migration, workflow linting, shell safety, native storage robustness, and test coverage. Adding new product scope would have increased release risk.
  Date/Author: 2026-04-14 / Codex
- Decision: Extract macOS preview publishing into a script instead of disabling shellcheck.
  Rationale: Disabling shellcheck would hide future workflow script defects. A script keeps GitHub Actions lintable and makes the release mutation path testable with normal shell tooling.
  Date/Author: 2026-04-14 / Codex

## Outcomes & Retrospective

The release audit produced 91 documented improvements across API validation, Python settings and CSV parsing, LLM cache safety, web trial state, React UI edge cases, native Tauri storage and provider discovery, release scripts, workflow lintability, `.gitignore`, and documentation. The most important practical outcome is that the standard local release gates now pass and the original clean-checkout doctor failure is fixed.

The remaining local environment gap is CocoaPods: `just doctor` passes but reports that CocoaPods is unavailable, and `just tauri-ios-test` exits at `_ios-deps` with `CocoaPods missing; install CocoaPods before running iOS Tauri init/build`. GitHub's iOS simulator workflow installs CocoaPods explicitly.

## Context and Orientation

The repository root contains a Python package in `src/pitgpt`, a React and Vite web frontend in `web`, a Tauri native target in `app`, shared policy and template data in `shared`, benchmark fixtures in `benchmarks`, release and maintenance scripts in `scripts`, and GitHub Actions workflows in `.github/workflows`. The standard task runner is `justfile`, which routes Python commands through `uv` and `mise`, web commands through `npm --prefix web`, and native checks through the Rust toolchain pinned by `mise.toml`.

A release-prep audit here means improving the project so the standard commands are easier to run, failures are more actionable, release scripts are safer, documentation matches the code, and tests cover behavior that could regress after packaging. It does not mean adding unrelated product features or changing the clinical safety policy without evidence.

## Plan of Work

First, inspect the project structure and run baseline checks such as `just doctor`, `just test`, `just typecheck`, web build/unit checks, and Tauri checks when available. Also scan for TODO markers, brittle scripts, missing ignores, inconsistent docs, and user-facing copy that would look unfinished in a release.

Next, make small cohesive fixes. Count each improvement explicitly so the final handoff can show that the request for at least fifty improvements was satisfied. Prefer changes that reduce release risk: clearer validation, stronger tests, better input handling, safer shell scripts, more deterministic docs, more accurate `.gitignore` coverage, and web/native parity fixes when practical.

Finally, rerun relevant checks. If broad `just ci` is practical in the current environment, run it. If it is blocked by local machine prerequisites, run the narrow gates that do work and document the blocker with the exact failing command.

## Concrete Steps

Run all commands from `/Users/peyton/.codex/worktrees/014d/pitgpt-proto` unless noted otherwise.

The initial orientation commands are:

    pwd
    git status --short --branch
    rg --files
    just doctor

The expected result is a clean starting worktree, a visible list of tracked surfaces, and either a successful doctor report or clear prerequisite failures such as missing `node_modules`, Xcode, or CocoaPods.

Final verification commands run from the repository root:

    ./bin/mise exec -- just doctor
    ./bin/mise exec -- just lint
    ./bin/mise exec -- just check
    ./bin/mise exec -- just test
    ./bin/mise exec -- just typecheck
    ./bin/mise exec -- just web-build
    ./bin/mise exec -- just web-unit
    ./bin/mise exec -- npm --prefix web run test:e2e:install
    ./bin/mise exec -- just web-test
    ./bin/mise exec -- just tauri-test
    ./bin/mise exec -- just audit
    ./bin/mise exec -- just parity-analysis
    ./bin/mise exec -- shellcheck scripts/*.sh

## Validation and Acceptance

Acceptance requires at least fifty concrete improvements or fixes in the working tree and a verification pass that exercises the changed areas. For Python behavior changes, run `just test` and `just typecheck`. For web changes, run `just web-build` and `just web-unit`, and use browser or Playwright checks when UI behavior changes. For Tauri or release script changes, run the relevant Rust, shell, or release preflight checks where the local environment supports them.

## Idempotence and Recovery

The audit should avoid destructive commands. Dependency installation uses repo-local commands such as `just setup` and `just web-install`. Generated directories such as `.mypy_cache`, `.pytest_cache`, `web/dist`, and `app/target` can be removed with `just clean` if local checks leave artifacts behind. If a command fails because a local prerequisite is missing, install through the repository's declared tooling rather than relying on untracked global state.

## Artifacts and Notes

Key final transcripts:

    just test: 173 passed in 19.89s.
    just web-unit: 30 passed.
    just web-test: 21 passed, 1 skipped.
    just tauri-test: 18 passed.
    just audit: uv pip check passed; npm audit found 0 vulnerabilities.
    just parity-analysis: Python/Rust analysis parity passed for 9 case(s).
    just check: hk check, actionlint, zizmor, mypy, ruff, cargo fmt, and cargo clippy passed.

## Interfaces and Dependencies

No new runtime service dependency is planned. Python dependencies must stay declared in `pyproject.toml`, web dependencies in `web/package.json`, Rust dependencies in `app/Cargo.toml`, and tool versions in `mise.toml`. Shell scripts should be POSIX-friendly or explicitly Bash with `set -euo pipefail`; Python automation should be invokable as modules where practical.

Revision note, 2026-04-14: Created the initial living plan so the release audit can be resumed from repository files alone.

Revision note, 2026-04-14: Updated progress, discoveries, decisions, outcomes, and verification evidence after completing the release-prep implementation and checks.
