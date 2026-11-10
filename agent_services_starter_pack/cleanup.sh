#!/usr/bin/env bash
# Deletes what the agent services starter pack created:
#   - the Agent Runtime instance, with its sessions and memories
#   - the staging bucket and its files
# It does not delete the system-created _Trace bucket, the observability
# setting, or the APIs.
#
# Usage: ./cleanup.sh   (asks you to type the project ID first)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
set -a
# shellcheck disable=SC1091
source .env
set +a
: "${PROJECT_ID:?Set PROJECT_ID in .env}"
: "${STAGING_BUCKET:?Set STAGING_BUCKET in .env}"

echo "This deletes, in project ${PROJECT_ID}:"
echo "  - Agent Runtime instance: ${AGENT_RUNTIME_NAME:-<none in .env>} (sessions and memories also)"
echo "  - Staging bucket: gs://${STAGING_BUCKET}"
read -r -p "Type the project ID to continue: " ANSWER
if [[ "${ANSWER}" != "${PROJECT_ID}" ]]; then
  echo "The text does not match. No change."
  exit 1
fi

PYTHON="python3"
[[ -x .venv/bin/python ]] && PYTHON=".venv/bin/python"

if [[ -n "${AGENT_RUNTIME_NAME:-}" ]]; then
  "${PYTHON}" deploy.py --delete
else
  echo "No AGENT_RUNTIME_NAME in .env. No agent to delete."
fi

if gcloud storage buckets describe "gs://${STAGING_BUCKET}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud storage rm --recursive "gs://${STAGING_BUCKET}" --project="${PROJECT_ID}"
else
  echo "The staging bucket does not exist. No change."
fi

echo "CLEANUP: DONE. The _Trace bucket and the observability setting remain."
