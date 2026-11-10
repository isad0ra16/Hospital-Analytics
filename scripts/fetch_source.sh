#!/usr/bin/env bash
# Recover the original RDRJ2401.dbc from the project's GitHub Release (archived copy of the
# exact file downloaded from DATASUS), then verify it against data/MANIFEST.json.
#
# Uses the GitHub REST API through the `gh` CLI (works in environments where GraphQL,
# used by `gh release download`, is unavailable). Without gh, download manually:
#   https://github.com/isad0ra16/Hospital-Analytics/releases/tag/data-rdrj2401
set -euo pipefail

REPO="${REPO:-isad0ra16/Hospital-Analytics}"
TAG="${TAG:-data-rdrj2401}"
ASSET="${ASSET:-RDRJ2401.dbc}"
DEST_DIR="${DEST_DIR:-data/raw}"
DEST="$DEST_DIR/$ASSET"

if [[ -e "$DEST" ]]; then
  echo "$DEST already exists; not downloading (verifying instead)."
else
  asset_id=$(gh api "repos/$REPO/releases/tags/$TAG" --jq ".assets[] | select(.name == \"$ASSET\") | .id")
  if [[ -z "$asset_id" ]]; then
    echo "Asset $ASSET not found in release $TAG of $REPO." >&2
    exit 1
  fi
  mkdir -p "$DEST_DIR"
  tmp="$DEST.partial"
  trap 'rm -f "$tmp"' EXIT
  gh api -H "Accept: application/octet-stream" "repos/$REPO/releases/assets/$asset_id" > "$tmp"
  mv "$tmp" "$DEST"
  chmod 0444 "$DEST"
  echo "Downloaded $DEST"
fi

uv run hospital-analytics verify
