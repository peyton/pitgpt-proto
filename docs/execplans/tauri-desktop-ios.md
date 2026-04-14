# Add Tauri Desktop And iOS Targets

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This repository uses the execution-plan rules in `~/.agents/PLANS.md`. Keep this document self-contained and update it whenever implementation decisions, commands, or outcomes change.

## Purpose / Big Picture

PitGPT currently runs as a Python package, FastAPI service, terminal UI, and Vite React web app. After this change, a user can also run PitGPT as a local Tauri app on macOS and as an iOS app with the offline trial workflow. The macOS app can discover local AI tools, prefer Ollama for offline protocol generation, and persist data in native app storage. The iOS app can start local templates, track check-ins, analyze results, and persist data offline, while leaving a typed provider slot for future on-device model work.

The observable outcome is that `just tauri-dev` launches the macOS app, `just tauri-test` runs Rust command tests, existing web/API commands still work, and CI has explicit jobs for Rust, Tauri macOS, and iOS simulator checks.

## Progress

- [x] (2026-04-14 00:00Z) Read the current Python, web, test, CI, and documentation structure.
- [x] (2026-04-14 00:00Z) Confirmed user decisions: macOS uses Ollama first, iOS ships offline core now, release builds assume Apple signing.
- [x] (2026-04-14 00:00Z) Created this ExecPlan before code changes.
- [x] (2026-04-14 09:00Z) Added shared template and safety-policy data used by Python, TypeScript, and Rust.
- [x] (2026-04-14 09:00Z) Added provider discovery and optional provider selection to the Python API without breaking OpenRouter defaults.
- [x] (2026-04-14 09:00Z) Added `src-tauri` Rust target with commands, local storage, macOS provider discovery, Ollama ingestion, and reserved iOS on-device provider.
- [x] (2026-04-14 09:00Z) Added frontend runtime adapters and Settings/Home UI for native providers.
- [x] (2026-04-14 09:00Z) Added Rust, web, native, and iOS build-path tests plus CI/release workflows.
- [x] (2026-04-14 09:00Z) Ran verification commands and documented results.

## Surprises & Discoveries

- Observation: The current web app already has useful Vitest and Playwright coverage, and API calls are centralized in `web/src/lib/api.ts`.
  Evidence: `web/tests/e2e/app.spec.ts` mocks `/api/ingest`, `/api/analyze`, and `/api/health`; storage and trial logic already have unit tests.
- Observation: Current ingestion is OpenRouter-only in `src/pitgpt/api/main.py`, while analysis and schedule generation are deterministic local code.
  Evidence: `/ingest` constructs `LLMClient` from `OPENROUTER_API_KEY`; `/analyze` calls `pitgpt.core.analysis.analyze`.
- Observation: Tauri iOS rejects `dev.pitgpt.native` because `native` is a reserved bundle identifier segment.
  Evidence: `just tauri-ios-test` panicked with `IdentifierInvalid { identifier: "dev.pitgpt.native", cause: ReservedKeyword { keyword: "native" } }`.
- Observation: The local machine has Xcode-side Tauri helpers but not CocoaPods.
  Evidence: after changing the identifier to `dev.pitgpt.app`, `just tauri-ios-test` reached `CocoaPods missing; install CocoaPods before running iOS Tauri init/build`.
- Observation: Zizmor requires signing-secret jobs to use a dedicated GitHub environment.
  Evidence: `just check` reported `secrets-outside-env` until macOS/iOS signing jobs were assigned `environment: apple-signing`.

## Decision Log

- Decision: Do not use a Python sidecar for Tauri.
  Rationale: iOS cannot depend on a local Python process, and the desktop app should be able to run core offline features without the FastAPI server.
  Date/Author: 2026-04-14 / Codex
- Decision: Use Ollama as the only fully offline macOS AI provider in this phase.
  Rationale: Ollama exposes local HTTP APIs for model listing and chat completion. Claude, Codex, and ChatGPT CLIs may require network or accounts, so they should be discovered but not treated as guaranteed offline providers.
  Date/Author: 2026-04-14 / Codex
- Decision: Reserve an `ios_on_device` provider but leave it unavailable.
  Rationale: The user wants later on-device iOS model work. Shipping a typed provider slot now avoids future schema churn without adding Core ML, MLX, llama.cpp, model-download, or bundled-model scope.
  Date/Author: 2026-04-14 / Codex
- Decision: Use `dev.pitgpt.client` as the Tauri bundle identifier.
  Rationale: It is valid for macOS and iOS, while the earlier `dev.pitgpt.native` value failed Tauri iOS validation because `native` is reserved. `dev.pitgpt.app` also built but produced a macOS warning because it ends in `.app`.
  Date/Author: 2026-04-14 / Codex
- Decision: Make `just tauri-ios-test` preflight Xcode and CocoaPods before invoking Tauri.
  Rationale: Tauri otherwise attempts an interactive/global CocoaPods install path. A clear preflight failure is safer and matches clean-checkout expectations.
  Date/Author: 2026-04-14 / Codex

## Outcomes & Retrospective

Implemented the native target and preserved the existing API/web paths. macOS Tauri debug builds produce `PitGPT.app` and a DMG locally. iOS simulator builds are wired through `just tauri-ios-test` and CI, but local execution stops at the documented CocoaPods prerequisite on this machine.

Verification completed:

- `./bin/mise exec -- uv run --python 3.12 pytest` passed: 123 tests.
- `./bin/mise exec -- uv run --python 3.12 mypy src/pitgpt/` passed.
- `npm --prefix web run test:unit` passed: 13 tests.
- `npm --prefix web run test:e2e` passed: 17 passed, 1 skipped.
- `npm --prefix web run build` passed.
- `cargo test --manifest-path src-tauri/Cargo.toml --all-targets` passed: 10 Rust tests.
- `just check` passed, including ruff, mypy, actionlint, zizmor, rustfmt, and clippy.
- `npm --prefix web run tauri:build -- --debug` passed and produced debug macOS bundles.
- `just tauri-ios-test` reached the expected local prerequisite boundary because CocoaPods is not installed.

## Context and Orientation

The repository root is a Python project with a `src/` layout. The main package lives in `src/pitgpt/`. Domain models are in `src/pitgpt/core/models.py`, local statistical analysis is in `src/pitgpt/core/analysis.py`, random schedule generation is in `src/pitgpt/core/schedule.py`, and research ingestion is in `src/pitgpt/core/ingestion.py`. The FastAPI app is in `src/pitgpt/api/main.py`.

The React app lives in `web/`. It uses Vite and TypeScript. Routes are defined in `web/src/App.tsx`, app state lives in `web/src/lib/AppContext.tsx`, browser storage helpers live in `web/src/lib/storage.ts`, HTTP API helpers live in `web/src/lib/api.ts`, and UI pages live under `web/src/pages/`.

Tauri is a framework that embeds a web frontend in a native shell and lets frontend code call Rust commands through an inter-process call named `invoke`. This implementation adds `src-tauri/` at the repository root. The Tauri app reuses the built React app from `web/dist`.

## Plan of Work

First, create shared data files for trial templates and the safety policy so Python, TypeScript, and Rust can consume the same content. Update Python modules to load those files and add tests that prove current API outputs remain stable.

Second, extend provider support. Add a provider registry in Python and Rust with stable kinds: `openrouter`, `ollama`, `claude_cli`, `codex_cli`, `chatgpt_cli`, and `ios_on_device`. Add `GET /providers` to FastAPI and allow `POST /ingest` to accept an optional `provider`. Keep current OpenRouter behavior as the default when no provider is supplied.

Third, add the Tauri Rust target. Define serializable Rust models that match the TypeScript and Python wire shapes. Implement local templates, schedule generation, local state JSON persistence, exports, macOS provider discovery, Ollama model discovery and ingestion, and the deterministic analysis command. The analysis command must match the Python benchmark expected outputs within existing tolerances.

Fourth, update the frontend. Add a runtime adapter that detects Tauri, calls Rust commands in native builds, and falls back to existing HTTP/localStorage behavior in web builds. Update Home to use the preferred provider for generated protocols. Update Settings to show native storage/provider state, macOS discovered tools, and iOS “on-device AI planned” reserved status.

Fifth, add tests and CI. Keep the existing Python, Vitest, and Playwright checks. Add Rust unit/integration tests, web unit tests for the runtime adapter and provider UI, native smoke tests where practical, iOS simulator smoke commands, GitHub Actions jobs for Rust/Tauri/iOS, and a release workflow that attaches signed artifacts to GitHub Releases.

## Concrete Steps

Run all commands from the repository root unless a command explicitly sets another directory.

1. Update shared data, Python API, and tests.
2. Add `src-tauri/Cargo.toml`, `src-tauri/tauri.conf.json`, Rust modules, and Tauri capabilities.
3. Add Tauri dependencies and scripts to `web/package.json`, then refresh `web/package-lock.json` with `npm --prefix web install`.
4. Add frontend runtime adapter modules and update pages/settings.
5. Add CI workflows and docs.
6. Run targeted commands:

    just test
    just web-unit
    just web-build
    just tauri-test
    just tauri-build

For iOS, run simulator build/test when the generated Tauri iOS project is available and Xcode is installed:

    just tauri-ios-build
    just tauri-ios-test

## Validation and Acceptance

The implementation is accepted when:

- `just test` passes existing and new Python tests.
- `just web-unit` passes existing and new Vitest tests.
- `just web-test` passes existing Playwright tests and added provider/offline path tests.
- `just tauri-test` passes Rust tests for commands, provider discovery, storage, schedule, and analysis parity.
- `just tauri-build` produces a macOS Tauri bundle locally or reaches the signing prerequisite boundary with a clear documented message.
- `just tauri-ios-build` builds the iOS target on macOS/Xcode runners or reaches the signing/provisioning prerequisite boundary with a clear documented message.
- The browser web app can still run with `just serve` plus `just web-dev`.
- The macOS Tauri app can start from a template without network access, persist state, analyze a trial, and show local provider discovery.
- The iOS app can start from a template, persist check-ins, analyze results, and show on-device AI as planned but unavailable.

## Idempotence and Recovery

All additions are additive. Re-running dependency installation should only update lockfiles when package versions change. Rust target build artifacts stay under `src-tauri/target/` and generated frontend output stays under `web/dist/`; both should be ignored by git. Native app data is stored under the platform app-data directory and can be cleared through the Settings UI or `clear_app_state`.

If Tauri iOS initialization cannot run on a machine without Xcode or Apple signing material, keep the config and commands in place and document the missing prerequisite in command output and CI notes. Do not remove the existing web/API paths to satisfy native builds.

## Interfaces and Dependencies

Rust dependencies should include `tauri`, `tauri-build`, `serde`, `serde_json`, `thiserror`, `reqwest`, `tokio`, `dirs`, `which`, `statrs`, `chrono`, and `uuid` if needed. Frontend dependencies should include `@tauri-apps/api` and `@tauri-apps/cli`.

The Rust command names exposed to the frontend are:

    get_templates
    generate_schedule
    analyze
    analyze_example
    load_app_state
    save_app_state
    clear_app_state
    export_file
    discover_ai_tools
    ingest_local

Provider kind strings are stable public values:

    openrouter
    ollama
    claude_cli
    codex_cli
    chatgpt_cli
    ios_on_device

`ios_on_device` must remain typed and reserved, with status `reserved` or `unsupported_platform`, until a later implementation adds a real runtime.

## Artifacts and Notes

Important implementation evidence and command transcripts will be added here as work proceeds.
