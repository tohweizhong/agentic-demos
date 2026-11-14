#!/usr/bin/env bash
# Check the tools, install kcmd into .tools/, and enable the APIs.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

fail() { echo "ERROR: $*" >&2; exit 1; }

echo "== Check tools"
command -v gcloud >/dev/null || fail "gcloud is not installed."
command -v bq >/dev/null || fail "bq is not installed. It is part of the Google Cloud CLI."
command -v node >/dev/null || fail "Node.js is not installed. Install Node 22.12 or later."
command -v npm >/dev/null || fail "npm is not installed."

node_version="$(node --version | sed 's/^v//')"
major="${node_version%%.*}"
rest="${node_version#*.}"
minor="${rest%%.*}"
if (( major < 22 || (major == 22 && minor < 12) )); then
  fail "Node ${node_version} is too old. kcmd needs Node 22.12 or later."
fi
echo "gcloud: $(gcloud --version 2>/dev/null | head -1)"
echo "node:   v${node_version}"

account="$(gcloud config get-value account 2>/dev/null || true)"
[[ -n "${account}" ]] || fail "No gcloud account. Run: gcloud auth login"
echo "account: ${account}"
echo "project: ${PROJECT_ID}  region: ${REGION}"

echo "== Install kcmd ${KCMD_VERSION} into .tools/"
npm install --prefix "${DEMO_DIR}/.tools" --no-fund --no-audit \
  "@google-cloud/kcmd@${KCMD_VERSION}"
kcmd --version

echo "== Enable APIs"
gcloud services enable dataplex.googleapis.com bigquery.googleapis.com \
  --project "${PROJECT_ID}"

echo "Setup is complete."
