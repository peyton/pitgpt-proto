#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/apple-release-preflight.sh <macos-dmg|ios-appstore> [--github-output-availability] [--write-files]

Validates Apple signing environment for PitGPT release workflows.

Options:
  --github-output-availability  Write available=true/false to $GITHUB_OUTPUT and exit 0 when secrets are missing.
  --write-files                 Decode the App Store Connect API key and, for iOS, the provisioning profile.
USAGE
}

mode="${1:-}"
if [ -z "$mode" ]; then
  usage
  exit 2
fi
shift

github_output_availability=false
write_files=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --github-output-availability)
      github_output_availability=true
      ;;
    --write-files)
      write_files=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
  shift
done

case "$mode" in
  macos-dmg)
    required=(
      APPLE_API_ISSUER
      APPLE_API_KEY
      APPLE_API_KEY_P8_B64
      APPLE_CERTIFICATE
      APPLE_CERTIFICATE_PASSWORD
      APPLE_SIGNING_IDENTITY
      APPLE_TEAM_ID
    )
    ;;
  ios-appstore)
    required=(
      APPLE_API_ISSUER
      APPLE_API_KEY
      APPLE_API_KEY_P8_B64
      APPLE_CERTIFICATE
      APPLE_CERTIFICATE_PASSWORD
      APPLE_DEVELOPMENT_TEAM
      APPLE_SIGNING_IDENTITY
      IOS_PROVISIONING_PROFILE_B64
    )
    ;;
  *)
    echo "Unknown Apple release mode: $mode" >&2
    usage
    exit 2
    ;;
esac

missing=()
for name in "${required[@]}"; do
  if [ -z "${!name:-}" ]; then
    missing+=("$name")
  fi
done

if [ "${#missing[@]}" -gt 0 ]; then
  if [ "$github_output_availability" = true ]; then
    printf '::notice title=Skipping Apple release step::Missing Apple secrets for %s: %s\n' "$mode" "${missing[*]}"
    if [ -n "${GITHUB_OUTPUT:-}" ]; then
      echo "available=false" >> "$GITHUB_OUTPUT"
    fi
    exit 0
  fi

  for name in "${missing[@]}"; do
    printf '::error title=Missing Apple signing secret::%s is required for %s\n' "$name" "$mode"
  done
  exit 1
fi

if [ "$github_output_availability" = true ] && [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "available=true" >> "$GITHUB_OUTPUT"
fi

if [ "$write_files" != true ]; then
  exit 0
fi

api_key_path="${APPLE_API_KEY_PATH:-private_keys/AuthKey.p8}"
mkdir -p "$(dirname "$api_key_path")"
if ! printf '%s' "$APPLE_API_KEY_P8_B64" | base64 -d > "$api_key_path"; then
  printf '::error title=Invalid Apple API key::APPLE_API_KEY_P8_B64 could not be decoded\n'
  exit 1
fi
chmod 600 "$api_key_path"

if [ "$mode" = "ios-appstore" ]; then
  profile_dir="${IOS_PROVISIONING_PROFILE_DIR:-$HOME/Library/MobileDevice/Provisioning Profiles}"
  profile_path="${IOS_PROVISIONING_PROFILE_PATH:-$profile_dir/PitGPT.mobileprovision}"
  mkdir -p "$(dirname "$profile_path")"
  if ! printf '%s' "$IOS_PROVISIONING_PROFILE_B64" | base64 -d > "$profile_path"; then
    printf '::error title=Invalid iOS provisioning profile::IOS_PROVISIONING_PROFILE_B64 could not be decoded\n'
    exit 1
  fi
fi
