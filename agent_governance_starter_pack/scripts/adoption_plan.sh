#!/usr/bin/env bash
# Outputs a tier-by-tier lateral adoption plan.
#
# Usage:
#   scripts/adoption_plan.sh --project PROJECT_ID [--region REGION]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need jq

PROJECT=""
REGION="us-central1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
  esac
done

[[ -n "${PROJECT}" ]] || { echo "ERROR: --project is required." >&2; exit 2; }

echo "Adoption Plan for Project: ${PROJECT}"
echo "Running discover.sh..."
DISCOVER_OUT="$("$(dirname "${BASH_SOURCE[0]}")/discover.sh" --project "${PROJECT}" --region "${REGION}" --markdown)"

echo "${DISCOVER_OUT}" | grep -E "Tier 2|Tier 3|Tier 4|Tier 5" || true

echo ""
echo "--- terraform.tfvars Snippets ---"
echo ""

echo "existing_mcp_servers = {"
echo "${DISCOVER_OUT}" | awk '/Cloud Run service:/ {
  name = $4
  url = $NF
  sub(/^.*\//, "", name)
  print "  " name " = {"
  print "    url            = \"" url "\""
  print "    tool_spec_file = \"../mcp-server/tool_spec.json\" # Update this path"
  print "  }"
}'
echo "}"

echo ""
echo "existing_agent_principals = ["
echo "${DISCOVER_OUT}" | awk '/principal:\/\// {
  print "  \"" $NF "\","
}'
echo "]"

echo ""
echo "--- Per-Agent Gateway Binding Instructions ---"
echo "To bind an agent to a gateway, run:"
echo "scripts/bind_existing_agent.sh --project ${PROJECT} --region ${REGION} --agent-id <AGENT_ID> [--egress-gateway GW_NAME] [--ingress-gateway GW_NAME]"
