# Add Experiment Conversations and Live Setup Chat

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This plan follows the repository guidance in `~/.agents/PLANS.md`. The plan is self-contained so a new contributor can understand the feature from this file and the current working tree alone.

## Purpose / Big Picture

When a user submits a new experiment idea, PitGPT should immediately move into a ChatGPT-style setup conversation instead of waiting on the home page and then jumping straight to protocol review. The chat should show a live, user-visible work trace as the model evaluates safety, reads sources, and drafts the next step. If the model needs more information, the chat asks follow-up questions; if it produces a protocol, the chat offers the existing protocol review and lock flow.

PitGPT currently stores only one active trial in `web/src/lib/types.ts` as `AppState.trial`. This work adds experiment conversations to app state so multiple in-progress experiment setup threads can appear in the sidebar. A conversation has messages, an unread flag, and optional generated ingestion data. The sidebar shows each in-progress experiment like a ChatGPT conversation, including a dot when new model updates have not been read. Opening that conversation clears the unread dot.

This feature touches three surfaces:

The API surface is the FastAPI server in `src/pitgpt/api/main.py`. It needs a streaming endpoint that emits setup progress events and the final `IngestionResult`.

The web surface is the Vite React app in `web/src`. It needs state, routing, sidebar, and chat UI changes.

The app surface is the Tauri native wrapper in `src-tauri`. Because Tauri renders the same React frontend, native compatibility mostly means preserving the state schema through native storage and routing native ingestion through the same chat abstraction. Where the HTTP API can stream progress, native ingestion will emit equivalent client-side trace messages around the existing `ingest_local` command.

## Progress

- [x] (2026-04-14 00:00Z) Read `~/.agents/PLANS.md`, mapped current API, web, storage, Tauri command, and test structure.
- [x] (2026-04-14 00:00Z) Decided to add a conversation layer around existing ingestion/trial data rather than replacing the trial and analysis engine.
- [x] (2026-04-14 00:00Z) Added API streaming endpoint and tests for line-delimited setup events.
- [x] (2026-04-14 00:00Z) Added web types, storage migration, state actions, and unit tests for conversations and unread clearing.
- [x] (2026-04-14 00:00Z) Added experiment chat route, updated new experiment submission, and rendered conversations with unread dots in the sidebar.
- [x] (2026-04-14 00:00Z) Preserved native app behavior by routing Tauri ingestion into the same chat screen and normalized state.
- [x] (2026-04-14 00:00Z) Ran focused and repo-level verification: Python tests, web unit tests, web build, Playwright, Tauri tests, and check hooks.

## Surprises & Discoveries

- Observation: The existing app has no server-side experiment persistence; all durable product state is client-side `localStorage` in web and `pitgpt_state.json` in Tauri.
  Evidence: `web/src/lib/storage.ts` stores `AppState` and `src-tauri/src/storage.rs` only saves and loads a JSON value.

- Observation: The existing OpenRouter API path returns a single JSON object, while Ollama has a Rust/Python streaming helper only for raw JSON text. A safe first implementation can stream high-level progress events without exposing hidden chain-of-thought.
  Evidence: `src/pitgpt/core/llm.py` has `LLMClient.complete()` and `OllamaClient.stream_json_text()`, while `src/pitgpt/api/main.py` only exposes `/ingest`.

- Observation: Playwright initially reused a stale Vite dev server on port 5173, which made the browser tests exercise the old home-page flow even after the code had changed.
  Evidence: The first failed browser snapshots showed `Home` still calling old ingest behavior and rendering a "Bad Gateway" alert. Killing the stale process and rerunning started a fresh Vite server; the same updated tests then exercised `/experiments/<id>` and passed.

- Observation: Setting a stopped conversation back to `draft` caused the chat page to immediately restart ingestion because `draft` is the auto-start state.
  Evidence: The cancellation Playwright test saw the stopped message but the composer stayed disabled. Changing the stopped state to `needs_review` left the conversation waiting for user input and made native cancellation request IDs stable.

## Decision Log

- Decision: Do not expose private model chain-of-thought. Show a live high-level work trace such as safety check, source review, and protocol readiness instead.
  Rationale: Users asked for a thinking trace, but the product should not claim access to hidden reasoning. High-level trace messages are useful and safe, and can be generated from the known ingestion pipeline.
  Date/Author: 2026-04-14 / Codex

- Decision: Store experiment setup conversations in `AppState.experiments` with a `currentExperimentId` pointer and keep `AppState.trial` for the single currently active randomized trial.
  Rationale: This is the smallest coherent change. It allows multiple in-progress setup conversations in the sidebar without broad analysis, check-in, or result rewrites.
  Date/Author: 2026-04-14 / Codex

- Decision: Use newline-delimited JSON over `fetch()` for the API stream instead of introducing a new dependency or full server-side persistence.
  Rationale: The repo already uses FastAPI and plain `fetch`; newline-delimited JSON works with POST bodies and can carry auth headers, unlike browser `EventSource`.
  Date/Author: 2026-04-14 / Codex

## Outcomes & Retrospective

Implemented the requested cross-surface behavior. New experiment submission now immediately creates a durable conversation and opens `/experiments/<id>`. The chat page shows the user's request, high-level live setup trace messages, follow-up questions for manual-review responses, blocked-scope messages, and a protocol-ready action that hands off to the existing protocol review and trial lock flow. The sidebar now lists experiment conversations and shows an unread dot for background updates until the conversation is opened.

The API now exposes `POST /experiments/ingest-stream` as newline-delimited JSON events while keeping `POST /ingest` unchanged. The Tauri app uses the same React chat route and emits equivalent client-side trace messages around the existing `ingest_local` command, so no Rust streaming primitive was needed.

The main intentional omission is multi-active-trial scheduling. The conversation layer supports multiple setup threads, but the existing `AppState.trial` still represents one active randomized trial. That matches the smallest coherent scope for this change and avoids rewriting check-ins, analysis, and result history.

## Context and Orientation

The ingestion pipeline turns a user query and optional documents into an `IngestionResult`. The Python implementation is in `src/pitgpt/core/ingestion.py`, and the FastAPI endpoint for web mode is `src/pitgpt/api/main.py` at `POST /ingest`. The Tauri local path is `web/src/lib/api.ts` calling native command `ingest_local`, implemented in `src-tauri/src/commands.rs` and `src-tauri/src/ingestion.rs`.

The React app is routed from `web/src/App.tsx`. `web/src/pages/Home.tsx` currently submits the new experiment form, waits for ingestion, stores the result in transient React state through `setIngestionResult`, and navigates to `/protocol`. `web/src/pages/ProtocolReview.tsx` reads that transient result, lets the user adjust labels, calls `createTrial()` from `web/src/lib/trial.ts`, stores the trial in `AppState.trial`, and navigates to `/trial`. `web/src/components/Layout.tsx` renders the sidebar.

Durable state is defined in `web/src/lib/types.ts` and normalized in `web/src/lib/storage.ts`. Current storage version is `4` after this change. The native app saves that same JSON through `save_app_state` in `src-tauri/src/commands.rs`. Therefore schema migration belongs in `web/src/lib/storage.ts`, not in Rust.

In this plan, an "experiment conversation" means a setup thread before or during a trial. It is not a clinical conversation and does not replace care. It stores messages shown in the chat UI. A "work trace" means short status messages generated by the app from pipeline events; it is not private model chain-of-thought.

## Plan of Work

First, add `POST /experiments/ingest-stream` to `src/pitgpt/api/main.py`. It should accept the same request shape as `/ingest` and return newline-delimited JSON events. Event objects should include `type`, `message`, and optional `result`. The endpoint should emit trace events before resolving documents/model work, then emit a final event containing the same `IngestionResult` returned by `/ingest`. Existing `/ingest` should remain unchanged for compatibility.

Second, extend `web/src/lib/types.ts` with `ExperimentConversation`, `ExperimentMessage`, and `ExperimentStatus` types. Add `experiments` and `currentExperimentId` to `AppState`. Bump `STORAGE_VERSION` in `web/src/lib/storage.ts` to `4` and normalize old states by creating an empty `experiments` array. Add helper functions in a new or existing web lib module for creating conversations, adding messages, setting unread state, and deriving a readable title from the user query.

Third, update `web/src/lib/api.ts` with `ingestExperimentStream()`. In web mode it should call `/api/experiments/ingest-stream` and parse newline-delimited JSON events from `ReadableStream`. In Tauri mode it should emit equivalent client-side trace events and call the existing native `ingest_local` command. This keeps the app surface working without adding a new Tauri streaming primitive.

Fourth, add a route such as `/experiments/:experimentId` to `web/src/App.tsx` and a page `web/src/pages/ExperimentChat.tsx`. `Home` should create a conversation immediately on submit, navigate to the chat route, and let the chat page own ingestion streaming. The chat page renders the user message, live trace messages, follow-up questions for manual review, a blocked message for blocked requests, and a protocol-ready action for generated protocols. If a protocol is ready, the action should put the existing `IngestionResult` into context and navigate to `/protocol`.

Fifth, update `web/src/components/Layout.tsx` to render in-progress conversations below "New Experiment". It should show a small dot when `experiment.unread` is true, and it should clear that unread flag when the route is opened. Sidebar should remain usable on mobile.

Sixth, update tests. Python API tests should prove the streaming endpoint emits trace and final result events. Web storage and helper tests should prove migration and unread clearing. Playwright should prove submit navigates immediately to chat, shows live setup text, then can continue to protocol review; another check should prove the sidebar unread dot appears and clears after opening.

## Concrete Steps

All commands run from `/Users/peyton/.codex/worktrees/7263/pitgpt-proto`.

After API edits, run:

    ./bin/mise exec -- uv run --python 3.12 pytest tests/test_api.py tests/test_ingestion.py

After web model edits, run:

    ./bin/mise exec -- npm --prefix web run test:unit

After UI edits, run:

    ./bin/mise exec -- npm --prefix web run build
    ./bin/mise exec -- npm --prefix web run test:e2e

After native-touching compatibility edits, run:

    ./bin/mise exec -- cargo test --manifest-path src-tauri/Cargo.toml --all-targets

For a final local gate if time allows, run:

    just ci

Commands actually run during implementation:

    ./bin/mise exec -- uv run --python 3.12 pytest tests/test_api.py tests/test_ingestion.py
    ./bin/mise exec -- npm --prefix web ci
    ./bin/mise exec -- npm --prefix web run test:unit
    ./bin/mise exec -- npm --prefix web run build
    ./bin/mise exec -- npm --prefix web run test:e2e
    ./bin/mise exec -- cargo test --manifest-path src-tauri/Cargo.toml --all-targets
    ./bin/mise exec -- just test
    ./bin/mise exec -- just check

## Validation and Acceptance

A human can verify the main behavior by starting the API and web frontend, opening the home page, typing a comparison, and submitting. The app should navigate immediately to `/experiments/<id>`. The chat should show the user's message and live setup trace messages while ingestion is running. When ingestion finishes with a protocol, the chat should show a protocol-ready assistant message and a button to review the generated protocol. When ingestion finishes with manual review, the chat should show follow-up questions. When ingestion is blocked, the chat should show the block explanation.

The sidebar should list in-progress setup conversations. If a conversation receives model updates while it is not the currently opened conversation, its row shows a dot. Opening that conversation clears the dot and persists the cleared state.

Existing behavior should still work: generated protocols can be reviewed, locked, checked in, stopped, analyzed, and exported as before. Tauri mocked runtime tests should continue to prove native ingestion cancellation and native state persistence.

## Idempotence and Recovery

The storage migration is additive. Existing states without `experiments` should normalize to an empty conversation list. Re-running tests and builds should not mutate source files except for generated build artifacts already ignored by the repo.

If the streaming endpoint fails, the web chat should show an assistant error message and leave the conversation in an error state rather than losing the user's original request. The user can start a new experiment or retry by submitting a new message.

## Artifacts and Notes

Verification summary:

    tests/test_api.py tests/test_ingestion.py: 47 passed
    web unit tests: 8 files passed, 39 tests passed
    web build: Vite production build completed
    Playwright: 22 passed, 2 mobile/desktop-specific skips
    Tauri cargo test: 21 passed
    just test: 179 passed
    just check: hk check hooks passed and tauri-lint passed

## Interfaces and Dependencies

In `src/pitgpt/api/main.py`, define an endpoint with this behavior:

    @app.post("/experiments/ingest-stream")
    async def ingest_stream_endpoint(req: IngestRequest):
        return StreamingResponse(...)

Events should be JSON objects serialized one per line. Minimum event types are `trace`, `result`, and `error`.

In `web/src/lib/types.ts`, define:

    export type ExperimentStatus = "draft" | "generating" | "needs_review" | "ready_to_lock" | "blocked" | "active" | "completed" | "error";

    export interface ExperimentMessage {
      id: string;
      role: "user" | "assistant" | "trace";
      content: string;
      createdAt: string;
      status?: "streaming" | "done" | "error";
      questions?: string[];
      ingestionResult?: IngestionResult;
    }

    export interface ExperimentConversation {
      id: string;
      title: string;
      createdAt: string;
      updatedAt: string;
      status: ExperimentStatus;
      unread: boolean;
      query: string;
      documents: string[];
      sourceNames: string[];
      ingestionResult?: IngestionResult | null;
      trialId?: string;
      messages: ExperimentMessage[];
    }

In `web/src/lib/api.ts`, define a streaming helper that accepts callbacks:

    export interface IngestStreamEvent {
      type: "trace" | "result" | "error";
      message: string;
      result?: IngestionResult;
    }

    export async function ingestExperimentStream(..., onEvent: (event: IngestStreamEvent) => void): Promise<IngestionResult>

In `web/src/lib/AppContext.tsx`, expose actions for creating a conversation, appending messages, setting its status/result, marking it read, and selecting the current experiment.

Plan revision note, 2026-04-14: Initial plan created after codebase reconnaissance. The key design choice is additive conversation state with high-level live trace events rather than exposing hidden model chain-of-thought.

Plan revision note, 2026-04-14: Updated after implementation and verification. Recorded the completed API, web, and app behavior, the stale-dev-server and cancellation discoveries, the actual verification commands, and the intentional omission of multi-active-trial scheduling.
