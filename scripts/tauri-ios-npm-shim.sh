#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
shim_dir="$repo_root/app/gen/apple"
shim_file="$shim_dir/package.json"

if [ ! -f "$repo_root/web/package.json" ] || [ ! -f "$repo_root/app/Cargo.toml" ]; then
  echo "Could not find PitGPT repo root at $repo_root" >&2
  exit 2
fi

mkdir -p "$shim_dir"
cat > "$shim_file" <<'JSON'
{
  "private": true,
  "scripts": {
    "tauri": "cd ../.. && ../web/node_modules/.bin/tauri"
  }
}
JSON
