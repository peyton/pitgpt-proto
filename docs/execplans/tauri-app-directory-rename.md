# Move Tauri Native App To app/

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. This plan follows the local requirements in `/Users/peyton/.agents/PLANS.md`.

## Purpose / Big Picture

PitGPT previously kept the Tauri native shell in Tauri's default source directory at the repository root. The requested repository shape is to move that native app to `app/`. After this change, a developer can run the same public commands, such as `just tauri-test`, `just tauri-build`, and `just tauri-ios-test`, and those commands will use `app/Cargo.toml` and `app/tauri.conf.json`. The visible proof is that local CI-style checks and Tauri build/test commands no longer reference the old directory and still pass.

## Progress

- [x] (2026-04-14T21:09Z) Read the current planning rules, confirmed the worktree is clean, and searched for repository references to the old Tauri directory.
- [x] (2026-04-14T21:10Z) Moved the checked-in Tauri directory to `app/` while preserving files with Git rename tracking.
- [x] (2026-04-14T21:12Z) Updated task runner recipes, npm Tauri entry points, scripts, workflows, tests, and documentation to use `app/`.
- [x] (2026-04-14T21:17Z) Fixed `app/tauri.conf.json` build commands after the macOS Tauri build showed they run from the repository root.
- [x] (2026-04-14T21:20Z) Fixed `just doctor` so `xcodebuild -version` is pipe-safe under `set -euo pipefail`.
- [x] (2026-04-14T21:22Z) Stabilized the unread sidebar Playwright test by waiting for the Settings route before releasing the mocked ingestion response.
- [x] (2026-04-14T21:23Z) Ran focused checks and the full local CI gate from the final edited state.
- [x] (2026-04-14T22:36Z) Verified the iOS simulator path reaches mise-managed CocoaPods, Tauri iOS project generation, web build, and Xcode invocation; local Xcode build-service execution is blocked by a host-level stall outside this repository.

## Surprises & Discoveries

- Observation: The rename affects release and preview automation, not only local Rust commands.
  Evidence: `.github/workflows/ci.yml`, `.github/workflows/macos-preview-release.yml`, `.github/workflows/release.yml`, `scripts/collect-tauri-artifacts.sh`, and `scripts/tauri-ios-npm-shim.sh` all needed path updates.

- Observation: Running Tauri from the repository root is no longer appropriate because the CLI's default project lookup expects the old directory name.
  Evidence: `web/package.json` now enters `app/` before invoking `../web/node_modules/.bin/tauri`.

- Observation: Tauri's `beforeBuildCommand` ran from the repository root even though the CLI process was launched from `app/`.
  Evidence: `just tauri-build` first failed with npm looking for `/Users/peyton/.codex/worktrees/31cb/web/package.json` when the command used `npm --prefix ../web run build`; changing it to `npm --prefix web run build` allowed the bundle to complete.

- Observation: `just doctor` could fail on a machine with Xcode because `head -n 1` closes the pipe while `xcodebuild -version` is still writing and `pipefail` turns that into exit 141.
  Evidence: `just doctor` failed with exit code 141 after printing `Xcode 26.5`; replacing `head -n 1` with `sed -n '1p'` made `just doctor` pass.

- Observation: The desktop unread-sidebar Playwright case was racing route cleanup.
  Evidence: The final-state CI rerun failed once because `.conversation-unread-dot` was missing; after waiting for the Settings heading before releasing the mocked ingestion response, the targeted test passed 5 repeated desktop runs and the full CI gate passed.

- Observation: The local machine cannot currently complete any Xcode build-system invocation that reaches Xcode's external tool discovery step.
  Evidence: `just tauri-ios-test` and a direct `xcodebuild` against `app/gen/apple/pitgpt-tauri.xcodeproj/project.xcworkspace` both reached `ExecuteExternalTool ... clang -v -E -dM` and then stalled. Sampling the child `clang` process showed it blocked in `write(2)`, while invoking the same `clang` command directly returned immediately. Unrelated Xcode builds on the host were already stuck in the same `SWBBuildService`/`clang -v -E -dM` state.

## Decision Log

- Decision: Keep the public command names `just tauri-*` and npm script names unchanged while changing their internal paths to `app/`.
  Rationale: The user asked to move the directory, not to rename the product surface. Preserving command names minimizes downstream churn.
  Date/Author: 2026-04-14 / Codex.

- Decision: Use Git's move command for the directory move.
  Rationale: This preserves history for reviewers and makes the structural rename explicit in Git.
  Date/Author: 2026-04-14 / Codex.

- Decision: Run the Tauri CLI from `app/` through the repo-local web package binary instead of passing a config path from the repository root.
  Rationale: Running from `app/` matches Tauri's expectations for local files such as `tauri.conf.json`, `capabilities/`, `icons/`, `build.rs`, and generated mobile projects.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

The native Tauri target now lives in `app/`, and all current automation, docs, tests, and release helpers use that path. The public commands stayed the same. The migration also fixed two unrelated but CI-relevant issues found during verification: the pipe-sensitive `just doctor` Xcode check and a flaky Playwright test. A follow-up change pinned CocoaPods in `mise.toml`, so `just setup` now installs the local `pod` executable needed for the iOS simulator path.

## Context and Orientation

The repository root contains a Python package in `src/pitgpt`, a Vite React frontend in `web`, and a Tauri v2 native target. Tauri is the framework that packages the React frontend into a native macOS and iOS shell while exposing Rust commands to frontend code. Before this plan, the Tauri target used Tauri's default source directory name; after this plan it lives under `app/`.

The native Rust crate is configured by `app/Cargo.toml` and `app/tauri.conf.json`. Generated Rust and mobile build outputs live under `app/target` and `app/gen`. The standard user-facing commands are defined in `justfile`, while the web package delegates Tauri CLI calls through scripts in `web/package.json`. GitHub Actions workflows run Rust, macOS, iOS simulator, preview, and release steps that must follow the new path.

## Plan of Work

Move the native target directory to `app/`. Then replace old path references in automation and source-controlled docs. The important executable paths are `justfile`, `.gitignore`, `scripts/tauri-ios-npm-shim.sh`, `scripts/collect-tauri-artifacts.sh`, `scripts/parity_analysis.py`, `.github/workflows/ci.yml`, `.github/workflows/macos-preview-release.yml`, `.github/workflows/release.yml`, `.github/dependabot.yml`, and tests in `tests/test_tooling_config.py`.

After path updates, run a search for stale references to the old directory and classify any remaining hits. Historical ExecPlans may remain as records when they describe past work, but current commands, documentation, tests, and workflow assertions should use `app/`. Then run formatting, tests, Rust lint/test, web tests, and the local CI gate until the repository is in a state that should pass GitHub CI.

## Concrete Steps

From `/Users/peyton/.codex/worktrees/31cb/pitgpt-proto`:

    git status --short
    rg -n --hidden "<old-tauri-directory-token>" -g '!*node_modules*' -g '!target' -g '!dist' -g '!.git'
    just check
    just test
    just web-build
    just web-unit
    just web-test
    just tauri-lint
    just tauri-test
    just ci

The final validation sequence completed as follows:

    just tauri-test: 21 Rust tests passed from app/Cargo.toml.
    just tauri-lint: cargo fmt and clippy passed from app/Cargo.toml.
    npm --prefix web run tauri -- --version: reported tauri-cli 2.10.1 from app/.
    npm --prefix web run tauri -- info: reported frontendDist ../web/dist and the expected app settings.
    just test: 179 Python tests passed.
    just web-build: Vite production build passed.
    just web-unit: 8 files and 39 tests passed.
    just web-test: 22 Playwright tests passed, 2 skipped.
    just parity-analysis: Python/Rust analysis parity passed for 9 cases.
    just tauri-build: produced app/target/release/bundle/macos/PitGPT.app and app/target/release/bundle/dmg/PitGPT_0.1.0_aarch64.dmg.
    scripts/collect-tauri-artifacts.sh macos-dmg: found the DMG under app/target.
    just doctor: passed and reported CocoaPods as installed after the follow-up toolchain pin.
    just ci: passed from the final edited state.
    just tauri-ios-test: generated app/gen/apple with CocoaPods from mise and reached xcodebuild; local completion was blocked by the host Xcode build-service stall described above.

## Validation and Acceptance

Acceptance is met for the repository-controlled migration and local CI gate. A repository search shows no current automation, test, README, AGENTS, or workflow references to the old path. `just tauri-test` passes using `app/Cargo.toml`, `just check` passes so GitHub workflow and tooling assertions agree with the new structure, and the full `just ci` command passes locally. Local iOS simulator execution requires Xcode and the mise-pinned CocoaPods tool installed by `just setup`; on this host, the command reaches Xcode and then hits a machine-level Xcode build-service stall that also affects unrelated projects.

## Idempotence and Recovery

The directory move is safe to inspect with `git status`. If an edit leaves a stale path, rerun the stale-reference search and update that file. Generated directories can be cleaned with `just clean`, which must also use the new `app/` paths after the migration.

## Artifacts and Notes

Initial search showed active references in `justfile`, `.gitignore`, scripts, workflow YAML files, `tests/test_tooling_config.py`, `README.md`, `AGENTS.md`, and several docs. Those are the active files that must be updated for the rename.

## Interfaces and Dependencies

No new dependencies are planned. The Rust crate remains named `pitgpt-tauri`, and frontend imports of `@tauri-apps/api` do not change. The public entry points remain `just tauri-dev`, `just tauri-build`, `just tauri-test`, `just tauri-lint`, `just tauri-ios-dev`, `just tauri-ios-build`, and `just tauri-ios-test`.

Plan revision note 2026-04-14T21:09Z: Created the plan after initial discovery so a future contributor can continue from the current repository state and understand why the native Tauri target is moving to `app/`.

Plan revision note 2026-04-14T21:12Z: Recorded the completed directory move and the choice to execute Tauri commands from `app/`.

Plan revision note 2026-04-14T21:23Z: Recorded validation results, the Tauri config command fix, the `just doctor` pipe fix, and the Playwright race fix discovered while proving the migration.

Plan revision note 2026-04-14T21:35Z: Recorded the follow-up decision to pin CocoaPods in `mise.toml` so iOS simulator prerequisites are repo-managed.
