#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/collect-tauri-artifacts.sh <macos-dmg|ios-ipa> <output-file>

Writes sorted Tauri release artifact paths to <output-file> and fails if none exist.
USAGE
}

mode="${1:-}"
output_file="${2:-}"

if [ -z "$mode" ] || [ -z "$output_file" ]; then
  usage
  exit 2
fi

mkdir -p "$(dirname "$output_file")"

case "$mode" in
  macos-dmg)
    if [ -d app/target/release/bundle ]; then
      find app/target/release/bundle -type f -name '*.dmg' -print | sort > "$output_file"
    else
      : > "$output_file"
    fi
    missing_title="Missing macOS artifact"
    missing_message="No DMG was produced"
    ;;
  ios-ipa)
    find app -type f -name '*.ipa' -print | sort > "$output_file"
    missing_title="Missing iOS artifact"
    missing_message="No IPA was produced"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown artifact mode: $mode" >&2
    usage
    exit 2
    ;;
esac

if [ ! -s "$output_file" ]; then
  printf '::error title=%s::%s\n' "$missing_title" "$missing_message"
  exit 1
fi
