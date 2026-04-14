# Harden CI and Apple Release Paths

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`,
`Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

The repo-level `AGENTS.md` asks agents to use an ExecPlan for complex changes. The local plan
rules live at `/Users/peyton/.agents/PLANS.md`, and this document follows those rules.

## Purpose / Big Picture

PitGPT should be easier to build from a clean checkout and less fragile when GitHub or Apple
release environments drift. After this change, CI runs should have bounded runtimes, redundant
pull request runs should cancel, Linux runner image drift should be explicit, Apple signing
preflight checks should be shared instead of duplicated YAML, official iOS release builds should
use App Store Connect export semantics with a unique build number, and release operators should
have a checked-in checklist for secrets and artifacts.

The observable outcome is that `just check` and the targeted tests pass, workflow files call
repo-local helper scripts, and release documentation tells a new operator exactly which secrets,
commands, and artifacts matter.

## Progress

- [x] (2026-04-14T14:56Z) Read the local planning rules and created this ExecPlan before editing.
- [x] (2026-04-14T14:56Z) Ran `claude -p` twice; the non-TTY run returned empty output, and the
  TTY run returned 55 improvement ideas.
- [x] (2026-04-14T15:03Z) Implemented CI reliability changes for runner pinning,
  concurrency, job timeouts, and clean-checkout tool declarations.
- [x] (2026-04-14T15:03Z) Implemented shared Apple release preflight and artifact
  collection scripts, then wired release workflows to those scripts.
- [x] (2026-04-14T15:03Z) Added Apple release privacy metadata, release docs, and justfile recipes for release preflight.
- [x] (2026-04-14T15:03Z) Added tests that protect the CI/release behavior and updated project docs.
- [x] (2026-04-14T15:15Z) Added a Renovate package group for Tauri npm and Cargo
  dependency updates.
- [x] (2026-04-14T15:13Z) Ran script smoke tests, focused tooling tests, `just check`,
  full pytest, web production build, and a debug Tauri bundle build.

## Surprises & Discoveries

- Observation: `claude -p` returned no output when run through the default non-TTY command path.
  Evidence: the first repo audit command ran for several minutes, exited with code 0, and emitted
  an empty stdout stream.
- Observation: `claude -p` produced output when attached to a TTY.
  Evidence: a one-word prompt returned "Hello.", and the 55-item audit completed after the TTY
  retry.
- Observation: `./bin/mise exec -- actionlint --version`, `zizmor --version`, and `act --version`
  reported concrete current versions even though `mise.toml` used `latest`.
  Evidence: actionlint 1.7.12, zizmor 1.24.1, and act 0.2.87 were printed locally.
- Observation: zsh treats `status` as a read-only variable.
  Evidence: initial shell smoke tests using `status=$?` failed with `zsh:1: read-only variable:
  status`; rerunning the same checks under `bash -lc` produced the intended script outputs.
- Observation: The Tauri resource setting copied the Apple privacy manifest into the macOS app
  bundle.
  Evidence: `find src-tauri/target/debug/bundle/macos/PitGPT.app -name
  'PrivacyInfo.xcprivacy' -print` returned
  `src-tauri/target/debug/bundle/macos/PitGPT.app/Contents/Resources/PrivacyInfo.xcprivacy`.

## Decision Log

- Decision: Implement a cohesive CI and Apple release hardening pass instead of trying to land all
  55 Claude ideas.
  Rationale: Several Claude suggestions need Apple Developer account knowledge or would change
  product identity, such as a new bundle identifier or App Store sandbox entitlements. The safer
  immediate value is to harden verifiable repo behavior and document the account-bound work.
  Date/Author: 2026-04-14 / Codex.
- Decision: Change official iOS release exports from `release-testing` to `app-store-connect` and
  pass `--build-number`.
  Rationale: Tauri's CLI documents `app-store-connect` as the package-ready App Store option and
  `release-testing` as the TestFlight option. Apple uploads also need monotonically distinct build
  numbers, so GitHub's run number is a deterministic CI source.
  Date/Author: 2026-04-14 / Codex.
- Decision: Keep macOS DMG release behavior as a signed/notarized outside-App-Store artifact, and
  document Mac App Store gaps instead of pretending the current DMG workflow is a MAS submission.
  Rationale: Tauri's DMG distribution guide identifies DMG as outside-App-Store distribution. A
  Mac App Store path would need sandbox entitlements and store packaging validated against the
  team's Apple account.
  Date/Author: 2026-04-14 / Codex.
- Decision: Do not add implicit Homebrew/CocoaPods installation to `just setup`.
  Rationale: The project guidance forbids undeclared global dependency installation at runtime.
  The existing CI can install CocoaPods, while local setup should diagnose missing iOS tooling and
  let the operator install it intentionally.
  Date/Author: 2026-04-14 / Codex.

## Outcomes & Retrospective

Implemented a focused CI and Apple release hardening pass. Main CI now pins Ubuntu jobs to
`ubuntu-24.04`, cancels stale PR runs, and sets per-job timeouts. The release workflows now call
shared scripts for Apple secret preflight, App Store Connect key/profile writing, and artifact
collection. Official iOS releases now use `app-store-connect` export with GitHub's run number as
the Tauri build number. The Tauri bundle includes `PrivacyInfo.xcprivacy`, local tooling pins
`just`, `actionlint`, `zizmor`, and `act`, Renovate groups tightly coupled Tauri npm and Cargo
dependencies, and release operators have `docs/release-checklist.md` plus `just
release-preflight`.

Verification completed:

- `./bin/mise exec -- just --evaluate`
- `GITHUB_OUTPUT=<temp> scripts/apple-release-preflight.sh macos-dmg --github-output-availability`
- `bash -lc 'scripts/apple-release-preflight.sh ios-appstore ...'` expecting missing-secret errors
- `bash -lc 'scripts/collect-tauri-artifacts.sh ios-ipa ...'` expecting a missing-artifact error
- `./bin/mise exec -- just test tests/test_tooling_config.py`
- `./bin/mise exec -- just check`
- `./bin/mise exec -- just test`
- `./bin/mise exec -- npm --prefix web ci`
- `./bin/mise exec -- npm --prefix web run build`
- `./bin/mise exec -- npm --prefix web run tauri -- build --debug`
- `find src-tauri/target/debug/bundle/macos/PitGPT.app -name 'PrivacyInfo.xcprivacy' -print`

The intentionally omitted items are Apple-account-bound or product-identity-bound changes:
renaming the bundle identifier, enabling Mac App Store sandbox entitlements, adding Mac App Store
packaging, and validating real provisioning profile bundle IDs. Those remain documented gaps in
`docs/release-checklist.md`.

## Context and Orientation

GitHub Actions workflows live under `.github/workflows/`. The main CI workflow is
`.github/workflows/ci.yml`; it currently runs Linux lint/check/test/web/audit jobs, macOS Rust
checks, a signed macOS build on pushes or manual dispatch, and an iOS simulator build. Official
release artifacts are built by `.github/workflows/release.yml`, while
`.github/workflows/macos-preview-release.yml` publishes a rolling prerelease named
`macos-preview`.

The native app is a Tauri v2 app under `src-tauri/`. Tauri is a framework that packages a web
frontend with Rust commands into desktop and mobile apps. The shared app configuration is
`src-tauri/tauri.conf.json`. The web frontend is a Vite React app under `web/`.

The current release workflows repeat Apple secret validation and file-writing shell code in YAML.
That makes the release path harder to test locally and easier to accidentally change in one
workflow but not another. This plan adds repo-local scripts under `scripts/`, tests under
`tests/`, and release docs under `docs/`.

## Plan of Work

First, update CI workflow metadata. Add a workflow-level concurrency group to the main CI workflow,
pin Ubuntu jobs to `ubuntu-24.04`, and add practical `timeout-minutes` values to every job in the
CI and release workflows. Update the iOS release command to use `--export-method
app-store-connect` and `--build-number "$GITHUB_RUN_NUMBER"`.

Next, create two small shell scripts. `scripts/apple-release-preflight.sh` validates the required
Apple signing environment for macOS DMG or iOS App Store builds and can write the App Store Connect
API key and iOS provisioning profile when requested. `scripts/collect-tauri-artifacts.sh` collects
expected `.dmg` or `.ipa` artifacts into a file and fails with a clear GitHub Actions error when
none are produced. Wire `.github/workflows/ci.yml`, `.github/workflows/release.yml`, and
`.github/workflows/macos-preview-release.yml` to those scripts.

Then, update clean-checkout and release operator surfaces. Pin tool versions in `mise.toml`, add
`just` to the managed tools, centralize Python 3.12 in the justfile, add release preflight and
cleanup recipes, add a privacy manifest resource for Apple bundles, and write release docs that
explain secrets, build numbers, preview vs official releases, and currently omitted Mac App Store
work.

Finally, add tests in `tests/test_tooling_config.py` or a new adjacent test file. The tests should
assert the workflows call the shared scripts, CI has concurrency and timeouts, iOS release uses
App Store Connect export plus build numbers, `mise.toml` declares the local command tools, and the
Apple release docs mention the required secrets.

## Concrete Steps

Run all commands from `/Users/peyton/.codex/worktrees/b136/pitgpt-proto`.

1. Edit workflow, script, docs, and test files with `apply_patch`.
2. Mark new shell scripts executable with `chmod +x`.
3. Run script smoke tests directly:
   `scripts/apple-release-preflight.sh macos-dmg --github-output-availability`
   with `GITHUB_OUTPUT` pointed at a temporary file, and
   `scripts/collect-tauri-artifacts.sh ios-ipa <tempfile>` against an empty target to confirm
   it fails clearly.
4. Run `just test tests/test_tooling_config.py`.
5. Run `just check`, `just test`, `npm --prefix web run build`, and a debug Tauri build because
   `src-tauri/tauri.conf.json` changed.

## Validation and Acceptance

The change is accepted when the focused tooling tests pass, `just check` passes, the Apple
preflight script can both report missing secrets as optional availability and fail when required
secrets are missing, and the workflows no longer contain duplicated Apple secret/file-writing
shell blocks. A human can verify the iOS App Store release path by reading
`.github/workflows/release.yml` and seeing `--export-method app-store-connect --build-number
"$GITHUB_RUN_NUMBER"`.

## Idempotence and Recovery

The new scripts should be safe to run repeatedly. Writing the App Store Connect key overwrites only
the configured key path, which defaults to `private_keys/AuthKey.p8` and is already ignored by
Git. Installing the iOS provisioning profile overwrites
`~/Library/MobileDevice/Provisioning Profiles/PitGPT.mobileprovision`, which is the existing
workflow path. Artifact collection writes only to the output file path provided by the caller.

If a workflow edit fails actionlint, revert only the faulty workflow hunk or adjust the script call
syntax; do not revert unrelated user changes. If a local machine lacks web dependencies, avoid
running full web builds unless required and report that limitation.

## Artifacts and Notes

The Claude TTY audit produced 55 ideas. The implemented subset maps mainly to Claude items 1, 2,
3, 13, 14, 16, 18, 23, 30, 31, 34, 39, 41, 42, 46, 48, and 49.

Key verification transcripts:

    just test
    150 passed in 19.05s

    just check
    ruff-format, ruff, mypy, actionlint, zizmor, cargo fmt, and cargo clippy passed

    npm --prefix web run tauri -- build --debug
    Finished 2 bundles at:
    src-tauri/target/debug/bundle/macos/PitGPT.app
    src-tauri/target/debug/bundle/dmg/PitGPT_0.1.0_aarch64.dmg

## Interfaces and Dependencies

`scripts/apple-release-preflight.sh` must accept one mode argument, either `macos-dmg` or
`ios-appstore`, followed by optional flags `--github-output-availability` and `--write-files`.
When `--github-output-availability` is present, missing secrets should produce a GitHub notice,
write `available=false` to `$GITHUB_OUTPUT`, and exit 0. Without that flag, missing secrets should
produce GitHub error annotations and exit nonzero.

`scripts/collect-tauri-artifacts.sh` must accept a mode argument, either `macos-dmg` or `ios-ipa`,
and an output file path. It must write sorted artifact paths to the output file and exit nonzero if
no matching artifacts exist.

Revision note: Initial plan created after the Claude TTY audit and before source edits, so the
selected implementation scope is explicit.
