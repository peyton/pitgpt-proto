#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
shim_dir="$repo_root/src-tauri/gen/apple"
shim_file="$shim_dir/package.json"

mkdir -p "$shim_dir"
cat > "$shim_file" <<'JSON'
{
  "private": true,
  "scripts": {
    "tauri": "cd ../../.. && npm --prefix web exec tauri --"
  }
}
JSON
