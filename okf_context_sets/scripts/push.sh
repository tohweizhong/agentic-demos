#!/usr/bin/env bash
# Push bundle/ into a Knowledge Catalog context set with kcmd.
# kcmd creates the entry group on the first push.
set -euo pipefail
source "$(dirname "$0")/_env.sh"
require_kcmd

WS="${DEMO_DIR}/workspace"
mkdir -p "${WS}"
cd "${WS}"

if [[ ! -f catalog.yaml ]]; then
  echo "== kcmd init (${ENTRY_GROUP_ID})"
  kcmd init --entry-group "${ENTRY_GROUP_ID}" --format okf
elif ! grep -q "entryGroup.${ENTRY_GROUP_ID}\$" catalog.yaml; then
  echo "ERROR: workspace/catalog.yaml points to another entry group:" >&2
  cat catalog.yaml >&2
  echo "Remove the workspace/ folder, then run this script again." >&2
  exit 1
fi

echo "== Copy bundle/ into workspace/bundle/"
mkdir -p bundle
cp "${DEMO_DIR}"/bundle/*.md "${DEMO_DIR}/bundle/_links.yaml" bundle/

echo "== kcmd push --dry-run"
kcmd push --dry-run

echo "== kcmd push"
kcmd push

echo "Push is complete. Context set: ${ENTRY_GROUP_NAME}"
