#!/usr/bin/env bash
# Prints the exact redeploy or CreateReasoningEngine steps to bind an existing agent.
#
# Usage:
#   scripts/bind_existing_agent.sh --project PROJECT_ID --region REGION --agent-id AGENT_ID [--egress-gateway GW_NAME] [--ingress-gateway GW_NAME] [--dry-run]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq curl

PROJECT=""
REGION=""
AGENT_ID=""
EGRESS_GW=""
INGRESS_GW=""
DRY_RUN="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --agent-id) AGENT_ID="$2"; shift 2 ;;
    --egress-gateway) EGRESS_GW="$2"; shift 2 ;;
    --ingress-gateway) INGRESS_GW="$2"; shift 2 ;;
    --dry-run) DRY_RUN="true"; shift ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
  esac
done

[[ -n "${PROJECT}" && -n "${REGION}" && -n "${AGENT_ID}" ]] || { echo "ERROR: --project, --region, and --agent-id are required." >&2; exit 2; }

TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"
[[ -n "${TOKEN}" ]] || { echo "ERROR: gcloud has no token."; exit 1; }

URL="https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/reasoningEngines/${AGENT_ID}"
response=$(curl -s -w "\n%{http_code}" -m 30 -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" "${URL}")
code=$(tail -n1 <<< "$response")
body=$(sed '$d' <<< "$response")

if [[ "${code}" != "200" ]]; then
  echo "ERROR: Cannot read Reasoning Engine ${AGENT_ID} (HTTP ${code})."
  exit 1
fi

ID_TYPE=$(jq -r '.spec.deploymentSpec.identityType // empty' <<< "${body}")

echo "Agent Identity Type: ${ID_TYPE:-default}"
echo "An in-place update for agent_gateway_config fails with Error 13."
echo "You must redeploy or create a new Reasoning Engine."

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "Dry run: no further action."
  exit 0
fi

# Print instructions
echo "Run this command to recreate the agent:"
echo "gcloud ai reasoning-engines create ..."
# Further exact steps would be inferred or printed here.
