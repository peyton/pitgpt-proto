# Release Checklist

PitGPT has three Apple-facing release paths:

- Main CI builds an optional signed macOS artifact on `master` pushes and manual runs when the
  `apple-signing` environment is fully configured.
- `macOS Preview Release` publishes the rolling `macos-preview` prerelease from `master` when
  native app inputs change.
- `Release` builds official signed macOS DMG artifacts and an iOS App Store Connect IPA when a
  GitHub Release is published.

## Version Bumps

Before creating a release tag, keep these versions in sync:

- `pyproject.toml`: `[project].version`
- `web/package.json`: `version`
- `app/tauri.conf.json`: top-level `version`
- `app/Cargo.toml`: package `version`

The iOS release workflow passes `--build-number "$GITHUB_RUN_NUMBER"` to Tauri so repeated
GitHub release builds get distinct Apple build numbers without changing the user-visible app
version.

## Required GitHub Environment

All Apple secrets must live in the `apple-signing` GitHub environment. Use `just
release-preflight-macos` and `just release-preflight-ios` locally to see the exact required names
without writing any secret files.

macOS DMG builds require:

- `APPLE_API_ISSUER`
- `APPLE_API_KEY`
- `APPLE_API_KEY_P8`
- `APPLE_CERTIFICATE`
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_SIGNING_IDENTITY`
- `APPLE_TEAM_ID`

iOS App Store Connect builds require:

- `APPLE_API_ISSUER`
- `APPLE_API_KEY`
- `APPLE_API_KEY_P8`
- `APPLE_CERTIFICATE`
- `APPLE_CERTIFICATE_PASSWORD`
- `APPLE_DEVELOPMENT_TEAM`
- `APPLE_SIGNING_IDENTITY`
- `IOS_PROVISIONING_PROFILE`

The helper script `scripts/apple-release-preflight.sh` writes the App Store Connect API key
contents to `APPLE_API_KEY_PATH`, defaulting to `private_keys/AuthKey.p8`. For iOS it also writes
the provisioning profile contents to
`~/Library/MobileDevice/Provisioning Profiles/PitGPT.mobileprovision` unless
`IOS_PROVISIONING_PROFILE_PATH` overrides that destination. Store both as plain secret contents,
not base64-encoded strings.

The rolling macOS preview workflow delegates tag, release-note, stale-asset cleanup, and artifact
upload work to `scripts/publish-macos-preview.sh` so the workflow stays lintable and the release
publishing logic remains testable outside GitHub Actions.

## Local Release Checks

Run these before publishing:

```sh
just ci
just release-preflight-macos
just release-preflight-ios
```

For iOS simulator parity, also run this on a macOS machine with Xcode after
`just setup` installs the mise-pinned CocoaPods tool:

```sh
just tauri-ios-test
```

## GitHub Release Flow

1. Confirm `master` is green in GitHub Actions.
2. Update versions and release notes.
3. Create and publish a GitHub Release for a `v*` tag.
4. Watch the `Release` workflow until both jobs succeed.
5. Download and inspect the attached DMG and IPA artifacts.

The official iOS release job uses Tauri's `app-store-connect` export method. The iOS simulator CI
job still uses a debug simulator build because it is a build-validation path, not a distribution
artifact path.

## Current App Store Gaps

The macOS workflow produces a signed DMG for distribution outside the Mac App Store. A Mac App
Store package is intentionally not claimed yet because it still needs Apple-team-specific sandbox
entitlements, provisioning profile validation, and packaging decisions.

The bundle includes `app/PrivacyInfo.xcprivacy` as a minimal Apple privacy manifest. If a
future dependency uses Apple required-reason APIs or starts collecting data, update that manifest
before release.
