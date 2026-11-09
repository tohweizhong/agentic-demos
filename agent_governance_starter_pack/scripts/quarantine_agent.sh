#!/usr/bin/env bash
# Emergency quarantine of one agent (backlog item 16). It removes the project
# IAM grants and the service account token creator grants of one agent principal,
# so the agent loses access to Google APIs and to the MCP server at once. It does
# not change the shared gateways or the Terraform-managed access policy.
#
#   scripts/quarantine_agent.sh --project PROJECT_ID --agent AGENT_ID            # plan only
#   scripts/quarantine_agent.sh --project PROJECT_ID --agent AGENT_ID --apply    # remove the grants
#
# After the incident, run terraform apply to restore the grants of a Terraform-managed agent.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq

PROJECT=""; AGENT=""; APPLY="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --apply) APPLY="true"; shift ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
  esac
done
[[ -n "${PROJECT}" && "${AGENT}" =~ ^[0-9]+$ ]] || { echo "ERROR: --project and a numeric --agent ID are required." >&2; exit 2; }
SUFFIX="reasoningEngines/${AGENT}"

PLAN="$(mktemp)"
gcloud projects get-iam-policy "${PROJECT}" --format=json 2>/dev/null \
  | jq -r --arg s "${SUFFIX}" '.bindings[]? | .role as $r | .members[]? | select(endswith($s)) | "project|\(.)|\($r)"' >> "${PLAN}" \
  || { echo "QUARANTINE: ERROR (cannot read the project IAM policy)"; exit 1; }
for sa in $(gcloud iam service-accounts list --project="${PROJECT}" --format='value(email)' 2>/dev/null); do
  gcloud iam service-accounts get-iam-policy "${sa}" --project="${PROJECT}" --format=json 2>/dev/null \
    | jq -r --arg s "${SUFFIX}" --arg sa "${sa}" '.bindings[]? | .role as $r | .members[]? | select(endswith($s)) | "sa:\($sa)|\(.)|\($r)"' >> "${PLAN}"
done

COUNT="$(wc -l < "${PLAN}")"
if [[ "${COUNT}" -eq 0 ]]; then echo "QUARANTINE: NOTHING (no grant names agent ${AGENT})"; rm -f "${PLAN}"; exit 0; fi
echo "Grants of agent ${AGENT}:"
while IFS='|' read -r where member role; do echo "  ${where}  ${role}"; done < "${PLAN}"
if [[ "${APPLY}" != "true" ]]; then echo "QUARANTINE: PLAN (${COUNT} grants). Run again with --apply to remove them."; rm -f "${PLAN}"; exit 0; fi

FAIL=0
while IFS='|' read -r where member role; do
  if [[ "${where}" == "project" ]]; then
    gcloud projects remove-iam-policy-binding "${PROJECT}" --member="${member}" --role="${role}" --condition=None --quiet >/dev/null || FAIL=$((FAIL + 1))
  else
    gcloud iam service-accounts remove-iam-policy-binding "${where#sa:}" --project="${PROJECT}" --member="${member}" --role="${role}" --quiet >/dev/null || FAIL=$((FAIL + 1))
  fi
done < "${PLAN}"
rm -f "${PLAN}"
[[ "${FAIL}" -eq 0 ]] && echo "QUARANTINE: DONE (${COUNT} grants removed from agent ${AGENT})" || { echo "QUARANTINE: PARTIAL (${FAIL} removals failed)"; exit 1; }
