#!/usr/bin/env bash
# Outputs a tier-by-tier lateral adoption plan.
#
# Usage:
#   scripts/adoption_plan.sh --project PROJECT_ID [--region REGION]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need jq curl gcloud

PROJECT=""
REGION="us-central1"
PREFIX=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
  esac
done

[[ -n "${PROJECT}" ]] || { echo "ERROR: --project is required." >&2; exit 2; }

echo "Adoption Plan for Project: ${PROJECT}"
echo "Running discover.sh..."
DISCOVER_CMD=("--project" "${PROJECT}" "--region" "${REGION}")
[[ -n "${PREFIX}" ]] && DISCOVER_CMD+=("--prefix" "${PREFIX}")
DISCOVER_JSON="$("$(dirname "${BASH_SOURCE[0]}")/discover.sh" "${DISCOVER_CMD[@]}")"

echo "--- terraform.tfvars Snippets ---"
echo ""

echo "existing_mcp_servers = {"
echo "${DISCOVER_JSON}" | jq -r '
  .registry as $reg | .cloud_run[] | select(.name as $rn | ($reg | map(.url // "" | test(($rn // "~") | sub("^https://";""); "i")) | any) | not) |
  "  \(.name) = {\n    url            = \"\(.url)\"\n    tool_spec_file = \"../mcp-server/tool_spec.json\"\n  }"
' || true
echo "}"

echo ""
PROJECT_NUMBER="$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)' 2>/dev/null || true)"
ORG_ID="$(gcloud projects get-ancestors "${PROJECT}" --format='value(id,type)' 2>/dev/null | awk '$2=="organization"{print $1}')"

echo "existing_agent_principals = ["
echo "${DISCOVER_JSON}" | jq -r --arg pn "${PROJECT_NUMBER}" --arg org "${ORG_ID}" --arg reg "${REGION}" '
  .agents[] | select(.starter_pack | not) |
  if .effective_identity then
    "  \"principal://\(.effective_identity)\","
  else
    "  \"principal://agents.global.org-\($org).system.id.goog/resources/aiplatform/projects/\($pn)/locations/\($reg)/reasoningEngines/\(.name)\","
  end
' || true
echo "]"
echo ""

WARN_SA=$(echo "${DISCOVER_JSON}" | jq -r '.agents[] | select((.starter_pack | not) and .identity_type == "SERVICE_ACCOUNT") | .name')
if [[ -n "${WARN_SA}" ]]; then
  echo "WARNING: The following agents use SERVICE_ACCOUNT instead of AGENT_IDENTITY. You must move them to AGENT_IDENTITY first before applying the principal-based access rules:"
  echo "${WARN_SA}"
  echo ""
fi

echo "--- Per-Agent Gateway Binding Instructions ---"
echo "To bind an agent to a gateway, run:"
echo "scripts/bind_existing_agent.sh --project ${PROJECT} --region ${REGION} --agent-id <AGENT_ID> [--egress-gateway GW_NAME] [--ingress-gateway GW_NAME]"
