# Release Audit Notes, 2026-04-14

This file records the release-prep improvements made during the broad audit pass. It is intentionally concrete so a reviewer can map the work back to code, tests, and verification commands.

## Improvements Implemented

1. Added a living release-prep ExecPlan at `docs/execplans/release-prep-audit-2026-04.md`.
2. Trimmed and de-duplicated configured CORS origins before FastAPI middleware registration.
3. Added a safe CORS fallback when `PITGPT_CORS_ORIGINS` is blank.
4. Trimmed caller-provided `X-Request-ID` values before returning them.
5. Rejected empty, overlong, and newline-containing request IDs.
6. Added structured FastAPI request-validation error responses with request IDs.
7. Encoded validation error details through FastAPI's JSON encoder.
8. Added `min_length=1` validation for ingestion request queries.
9. Rejected non-positive LLM timeout settings.
10. Rejected non-positive LLM max token settings.
11. Rejected non-positive per-document ingestion limits.
12. Rejected non-positive total ingestion limits.
13. Rejected non-finite LLM timeouts such as `nan`.
14. Made boolean environment parsing explicit for both true and false values.
15. Rejected misspelled boolean environment values instead of silently treating them as false.
16. Read local text fixtures and JSON files with explicit UTF-8 encoding.
17. Replaced quadratic duplicate CSV row detection with `Counter`-based detection.
18. Rejected non-numeric `secondary_scores` entries in observation CSV input.
19. Trimmed CSV `confounders` keys and values.
20. Dropped blank CSV `confounders` entries.
21. Trimmed CSV `deviation_codes` entries.
22. Dropped blank CSV `deviation_codes` entries.
23. Read LLM cache files with explicit UTF-8 encoding.
24. Wrote LLM cache files through a temporary file and atomic replace.
25. Trimmed ingestion queries before deterministic safety checks and provider prompts.
26. Treated zero ingestion limit overrides as invalid instead of falling through to defaults.
27. Trimmed provider-returned string lists before storing them.
28. Normalized blank optional strings to `None`.
29. Moved `just doctor`'s `web/node_modules` check before the Tauri CLI invocation.
30. Added coverage output ignores to `.gitignore`.
31. Added `.env.*` ignores while preserving `.env.example`.
32. Added npm/yarn debug log ignores.
33. Made the iOS Tauri npm shim fail clearly when invoked outside the repo root.
34. Made iOS provisioning profile output private with `chmod 600`.
35. Added tests for Apple release preflight file permissions.
36. Added tests for the iOS npm shim's non-repo-root failure path.
37. Made native app state saves atomic with a temporary file and rename.
38. Rejected `..` as a native export filename.
39. Rejected control characters in native export filenames.
40. Added a native storage test for replacing stale temporary state files.
41. Filtered blank Ollama model names in native provider discovery.
42. Sorted Ollama model names for stable UI output.
43. De-duplicated Ollama model names.
44. Centralized native ingestion document limits as named constants.
45. Trimmed native Ollama query prompts.
46. Required `block_reason` on native block ingestion results.
47. Added native tests for trimmed prompts and block-result contracts.
48. Trimmed stored API tokens in the web client.
49. Removed the stored API token when the settings field is cleared.
50. Centralized web API error-message extraction.
51. Used structured API error messages when validation details are arrays.
52. Made web provider discovery tolerate network failures.
53. Attached browser download anchors to the document and removed them after click.
54. Added a terminal newline to CSV exports.
55. Validated restored web provider settings against known provider kinds.
56. Validated restored reminder times against `HH:MM`.
57. Filtered restored local-AI consent settings to known boolean provider entries.
58. Normalized restored trials without mutating imported objects.
59. Trimmed restored condition labels.
60. Made `createTrial` avoid mutating the ingestion result.
61. Made locked trials keep a protocol copy consistent with the stored ingestion copy.
62. Clamped current-period math before day one.
63. Clamped days-left math before day one.
64. Rejected backfills with invalid dates.
65. Rejected backfills outside the trial day range.
66. Required adverse-event streaks to be truly consecutive days.
67. Added web trial tests for mutation safety, date clamping, backfill bounds, and streak detection.
68. Added per-source and total-source constants for web source uploads.
69. Rejected duplicate attached source text.
70. Rejected attached sources above the 40,000-character total.
71. Cleared stale source errors after a successful attachment.
72. Reset irritation, adherence, severity, and note disclosure state after daily check-in.
73. Reset backfill form controls after a saved backfill.
74. Preserved generated protocol labels when the user locks without typing overrides.
75. Added fallback safety and evidence badge rendering for unexpected provider values.
76. Changed the protocol-review secondary action from "Edit Conditions" to "Start Over".
77. Calculated Settings storage size from the current normalized state.
78. Aligned Settings' displayed version with the package version, `v0.1.0`.
79. Made result chart dot keys stable when duplicate day indexes exist.
80. Rendered missing confidence intervals as `—` instead of `undefined`.
81. Clamped the selected result-history index when restored history changes.
82. Added web API tests for token trimming/clearing and structured errors.
83. Added web storage tests for provider, reminder, consent, and label migration.
84. Added Python API tests for CORS parsing and request ID handling.
85. Added Python settings tests for invalid booleans, non-positive values, and non-finite values.
86. Extracted rolling macOS preview publication into `scripts/publish-macos-preview.sh`.
87. Removed a long inline workflow shell block that made actionlint hang through shellcheck integration.
88. Added a preview-publish script environment preflight before any `gh` release mutations.
89. Added a test that the preview-publish script fails before GitHub calls when CI context is missing.
90. Documented the preview-publish script in the release checklist.
91. Updated `AGENTS.md` so future agents know about the shared preview publishing script.

## Verification Evidence

The following commands passed during the final verification pass:

- `just test`: 173 passed.
- `just typecheck`: no mypy issues in 26 source files.
- `just web-build`: Vite production build completed.
- `just web-unit`: 30 passed.
- `cargo test --manifest-path app/Cargo.toml --all-targets`: 18 passed.
- `cargo fmt --manifest-path app/Cargo.toml -- --check`: passed.
- `just doctor`: passed, with the expected local warning that CocoaPods is not installed.
- `just lint`: passed all pre-commit hooks.
- `just check`: passed hk check plus Tauri fmt/clippy.
- `just audit`: `uv pip check` passed and npm audit found 0 vulnerabilities.
- `just parity-analysis`: Python/Rust analysis parity passed for 9 cases.
- `just web-test`: 21 passed, 1 skipped across desktop/mobile Playwright projects.
- `shellcheck scripts/*.sh`: passed.

`just tauri-ios-test` was attempted and stopped at `_ios-deps` because CocoaPods is not installed in this local environment. The GitHub iOS simulator workflow installs CocoaPods before running that build path.
