# MedGemma 1.5 Workflow Expansion Across API, Web, Tauri, CLI, and Just

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows `~/.agents/PLANS.md` and is written so a new contributor can execute and verify the feature from this file plus the current repository state.

## Purpose / Big Picture

After this change, a motivated home-lab user can open PitGPT and run three MedGemma-focused workflows end-to-end: genotype-guided routine hypotheses, multi-omics crossover design, and adverse-signal clinician escalation. The same workflow contract is shared across Python API, web, Tauri native path, CLI commands, and `just` wrappers, so behavior remains aligned across surfaces. The user can verify this by listing workflows, launching each demo, and observing that `workflow_id` is preserved in ingest requests and results while safety boundaries remain in force.

## Progress

- [x] (2026-04-22 08:41Z) Added shared workflow contract at `shared/workflows.json` with three distinct workflow definitions, UI metadata, and deterministic demo payloads.
- [x] (2026-04-22 08:49Z) Added Python workflow runtime module and settings support for MedGemma defaults and workflow/provider model overrides.
- [x] (2026-04-22 08:57Z) Extended API ingest request model with `workflow_id`, added workflow discovery/demo endpoints, and threaded workflow scaffolding into ingestion calls.
- [x] (2026-04-22 09:08Z) Added CLI workflow command group (`list`, `run`, `demo`, `demo-all`) and justfile wrappers (`workflow-list`, `workflow-demo`, `workflow-demo-all`).
- [x] (2026-04-22 09:19Z) Added Tauri workflow parity (`list_workflows` command and `workflow_id` propagation through `ingest_local`).
- [x] (2026-04-22 09:34Z) Added web workflows page, navigation route, abstract workflow assets, and demo-launch flow into experiment chat with workflow propagation.
- [x] (2026-04-22 09:44Z) Added and updated Python/web/e2e tests for workflow endpoints, workflow CLI, ingestion scaffolding, and web workflow demos.
- [ ] Run full verification set (`pytest`, `web unit`, `playwright`, `cargo test`, `just check`) and resolve any regressions.
- [ ] Finalize docs updates and capture outcomes with exact validation evidence.

## Surprises & Discoveries

- Observation: Rust command argument mapping already supports camelCase calls from web (`requestId` to `request_id`), so adding `workflowId` on the web side remained compatible with `workflow_id` in Rust.
  Evidence: Existing cancellation flow used `requestId` successfully before this change; new `workflow_id` follows the same Tauri argument mapping path.

## Decision Log

- Decision: Keep MedGemma defaults workflow-scoped rather than changing global default model selection.
  Rationale: This preserves existing generic ingestion behavior while allowing workflow-specific model policy and fallback warnings.
  Date/Author: 2026-04-22 / Codex

- Decision: Store workflow contract in `shared/workflows.json` and parse it independently in Python and Rust.
  Rationale: Shared JSON keeps cross-surface consistency with minimal coupling and no runtime network dependency.
  Date/Author: 2026-04-22 / Codex

- Decision: Keep safety policy hard boundaries intact while enriching escalation workflow outputs.
  Rationale: User requested ambitious genomics workflows, but autonomous diagnosis/treatment remains out of scope for current policy architecture.
  Date/Author: 2026-04-22 / Codex

## Outcomes & Retrospective

The feature is now implemented across shared data contracts, API endpoints, CLI commands, native command parity, and web UX entrypoints. Remaining work is final verification and any follow-up fixes required by failing checks. The resulting design keeps model selection controllable by workflow and environment while preserving current safety direction.

## Context and Orientation

The shared workflow source of truth is `shared/workflows.json`. Python loads this via `src/pitgpt/core/workflows.py` and applies scaffolding in `src/pitgpt/core/ingestion.py`. API endpoints are in `src/pitgpt/api/main.py`. CLI command surfaces live in `src/pitgpt/cli/main.py`, with `justfile` wrappers for local automation.

The web app uses shared APIs from `web/src/lib/api.ts`, type definitions in `web/src/lib/types.ts`, and page routes in `web/src/App.tsx`. Workflow UX is rendered in `web/src/pages/Workflows.tsx` and launched into experiment chat in `web/src/pages/ExperimentChat.tsx`. Visual assets are in `web/public/workflow-assets/`.

The Tauri native path routes ingestion through `app/src/commands.rs` and `app/src/ingestion.rs`, with workflow loading in `app/src/workflows.rs` and model structs in `app/src/models.rs`.

## Plan of Work

The implementation keeps contracts additive. First define shared workflows and runtime parsing in Python/Rust. Then thread `workflow_id` through all ingest entry points so workflow context can affect prompt scaffolding and model selection. Add workflow catalog APIs and CLI/native command entry points. Add the web workflows page and demo launch flow. Finally add tests for each layer and run verification.

## Concrete Steps

All commands run from repository root:

    ./bin/mise exec -- uv run --python 3.12 pytest tests/test_workflows.py tests/test_api.py tests/test_ingestion.py tests/test_cli.py
    ./bin/mise exec -- npm --prefix web run test:unit
    ./bin/mise exec -- npm --prefix web run test:e2e
    ./bin/mise exec -- cargo test --manifest-path app/Cargo.toml --all-targets
    ./bin/mise exec -- just check

## Validation and Acceptance

Acceptance criteria:

1. `GET /workflows` returns all three workflow IDs and UI metadata.
2. `GET /workflows/{workflow_id}/demo` returns deterministic demo payloads.
3. `POST /ingest` and `POST /experiments/ingest-stream` accept `workflow_id` and include workflow-derived scaffolding in prompt construction.
4. CLI commands `pitgpt workflow list/run/demo/demo-all` execute and return valid ingestion output.
5. `just workflow-list`, `just workflow-demo workflow=<id>`, and `just workflow-demo-all` run successfully.
6. Web `/workflows` page renders all cards and each “Run Demo” launches experiment chat.
7. Tauri `list_workflows` and `ingest_local(...workflow_id...)` are callable and compile/test cleanly.

## Idempotence and Recovery

Changes are additive and safe to re-run. Workflow demos are deterministic at request payload level. If provider/model defaults are unavailable, runtime falls back to configured baseline models and emits warning metadata. If a command fails due unavailable credentials or local model runtime, rerun after setting env vars or starting Ollama.

## Artifacts and Notes

Workflow assets are committed as static SVG files under `web/public/workflow-assets/` to keep demos deterministic and offline-capable in web and Tauri shells.

## Interfaces and Dependencies

Key interfaces added:

- Python:
  - `src/pitgpt/core/workflows.py` (`WorkflowDefinition`, `WorkflowDemoPayload`, model resolution helpers)
  - `src/pitgpt/api/main.py` adds `/workflows`, `/workflows/{workflow_id}/demo`, and `workflow_id` ingestion request support
- CLI:
  - `pitgpt workflow list`
  - `pitgpt workflow run --workflow ... --query ...`
  - `pitgpt workflow demo --workflow ...`
  - `pitgpt workflow demo-all`
- Tauri:
  - `list_workflows` command
  - `ingest_local` accepts `workflow_id`
- Web:
  - `/workflows` route and workflow demo launcher
  - API client methods `listWorkflows()` and `getWorkflowDemo()`

Plan revision note, 2026-04-22: Initial implementation ledger created during active rollout; progress entries and final verification evidence will be updated as execution completes.
