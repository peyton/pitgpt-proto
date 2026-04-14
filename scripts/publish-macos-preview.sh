#!/usr/bin/env bash
set -euo pipefail

required_env=(
  ARTIFACTS_FILE
  GITHUB_REPOSITORY
  GITHUB_RUN_ID
  GITHUB_SERVER_URL
  GITHUB_SHA
  PREVIEW_TAG
  PREVIEW_TITLE
  RUNNER_TEMP
)

for name in "${required_env[@]}"; do
  if [ -z "${!name:-}" ]; then
    printf '::error title=Missing preview release environment::%s is required\n' "$name"
    exit 2
  fi
done

if [ ! -s "$ARTIFACTS_FILE" ]; then
  printf '::error title=Missing macOS preview artifacts::%s is empty or missing\n' "$ARTIFACTS_FILE"
  exit 1
fi

release_notes="$RUNNER_TEMP/macos-preview-notes.md"
run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

cat > "$release_notes" <<NOTES
Automated macOS preview build from master.

Commit: ${GITHUB_SHA}
Run: ${run_url}

This release is replaced whenever macOS app inputs change on master.
NOTES

if gh api "repos/${GITHUB_REPOSITORY}/git/ref/tags/${PREVIEW_TAG}" >/dev/null 2>&1; then
  gh api \
    --method PATCH \
    "repos/${GITHUB_REPOSITORY}/git/refs/tags/${PREVIEW_TAG}" \
    -f sha="$GITHUB_SHA" \
    -F force=true >/dev/null
else
  gh api \
    --method POST \
    "repos/${GITHUB_REPOSITORY}/git/refs" \
    -f ref="refs/tags/${PREVIEW_TAG}" \
    -f sha="$GITHUB_SHA" >/dev/null
fi

if gh release view "$PREVIEW_TAG" >/dev/null 2>&1; then
  gh release edit "$PREVIEW_TAG" \
    --target "$GITHUB_SHA" \
    --title "$PREVIEW_TITLE" \
    --notes-file "$release_notes" \
    --prerelease
else
  gh release create "$PREVIEW_TAG" \
    --target "$GITHUB_SHA" \
    --title "$PREVIEW_TITLE" \
    --notes-file "$release_notes" \
    --prerelease \
    --latest=false
fi

release_id="$(gh api "repos/${GITHUB_REPOSITORY}/releases/tags/${PREVIEW_TAG}" --jq '.id')"
gh api "repos/${GITHUB_REPOSITORY}/releases/${release_id}/assets" --paginate --jq '.[].id' |
  while IFS= read -r asset_id; do
    if [ -n "$asset_id" ]; then
      gh api --method DELETE "repos/${GITHUB_REPOSITORY}/releases/assets/${asset_id}" >/dev/null
    fi
  done

while IFS= read -r artifact; do
  gh release upload "$PREVIEW_TAG" "$artifact" --clobber
done < "$ARTIFACTS_FILE"
