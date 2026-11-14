#!/usr/bin/env bash
# Read-only posture check (backlog item 12). Finds stale grants and missing gateway bindings.
# Sources: the project allow policy, IAP policy V2 access policies, service
# account policies, and IAP policy V1 bindings on Agent Registry entries.
# A stale grant names the principal of an agent that no longer exists.
#
#   scripts/doctor.sh --project PROJECT_ID --region REGION
#
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq curl

PROJECT=""
REGION=""
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
[[ -n "${REGION}" ]] || { echo "ERROR: --region is required." >&2; exit 2; }

TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"
[[ -n "${TOKEN}" ]] || { echo "DOCTOR: ERROR (gcloud has no token)"; exit 1; }
H=(-s -m 30 -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}")

IAM="$(gcloud projects get-iam-policy "${PROJECT}" --format=json 2>/dev/null)" || { echo "DOCTOR: ERROR (cannot read the project IAM policy)"; exit 1; }
APOL="$(curl "${H[@]}" "https://iam.googleapis.com/v3/projects/${PROJECT}/locations/global/accessPolicies")"

SA_PRINCIPALS=""
for sa in $(gcloud iam service-accounts list --project="${PROJECT}" --format="value(email)" 2>/dev/null); do
  sa_iam=$(gcloud iam service-accounts get-iam-policy "${sa}" --project="${PROJECT}" --format=json 2>/dev/null)
  if [[ -n "${sa_iam}" ]]; then
    p=$(jq -r --arg sa "${sa}" '.bindings[]? | .role as $r | .members[]? | select(test("reasoningEngines/")) | "\(.)\t\($r) on \($sa)"' <<<"${sa_iam}")
    if [[ -n "${p}" ]]; then
      SA_PRINCIPALS+="${p}
"
    fi
  fi
done

# IAP policy V1 keeps its rules as IAM bindings (roles/iap.egressor) on the IAP
# resource of each Agent Registry entry (item 19). Read them for mcpServers,
# endpoints, and agents in the region.
V1_PRINCIPALS=""
for kind in mcp-servers endpoints agents; do
  case "${kind}" in mcp-servers) iap_type="mcpServers" ;; *) iap_type="${kind}" ;; esac
  for id in $(gcloud agent-registry "${kind}" list --location="${REGION}" --project="${PROJECT}" --format="value(name.basename())" 2>/dev/null); do
    pol=$(curl "${H[@]}" -X POST -H "Content-Type: application/json" -d '{"options":{"requestedPolicyVersion":3}}' \
      "https://iap.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/iap_web/agentRegistry/${iap_type}/${id}:getIamPolicy")
    p=$(jq -r --arg t "${iap_type}/${id}" '.bindings[]? | .role as $r | .members[]? | select(startswith("principal://") and test("reasoningEngines/")) | "\(.)\tIAP V1 \($r) on \($t)"' <<<"${pol}" 2>/dev/null)
    if [[ -n "${p}" ]]; then
      V1_PRINCIPALS+="${p}
"
    fi
  done
done

PRINCIPALS="$( { jq -r '.bindings[]? | .role as $r | .members[]? | select(test("reasoningEngines/")) | "\(.)\t\($r)"' <<<"${IAM}";
  jq -r '.accessPolicies[]? | (.name | split("/") | last) as $p | .details.rules[]? | .principals[]? | select(test("reasoningEngines/")) | "\(.)\taccess policy \($p)"' <<<"${APOL}";
  [[ -n "${SA_PRINCIPALS}" ]] && echo "${SA_PRINCIPALS}";
  [[ -n "${V1_PRINCIPALS}" ]] && echo "${V1_PRINCIPALS}";
  } | grep -v '^$' | sort -u || true)"

HAS_GATEWAYS="false"
if gcloud network-services agent-gateways list --location="${REGION}" --project="${PROJECT}" --format="value(name)" 2>/dev/null | grep -q .; then
  HAS_GATEWAYS="true"
fi

if [[ -z "${PRINCIPALS}" ]]; then echo "DOCTOR: CLEAN (no agent principal is named in the project allow policy or the IAP access policies)"; exit 0; fi

STALE=0; LIVE=0; MISSING_GW=0; CHECKED_GW=" "
while IFS=$'\t' read -r member where; do
  path="$(sed -E 's#.*/resources/aiplatform/(projects/[^/]+/locations/[^/]+/reasoningEngines/[0-9]+).*#\1#' <<<"${member}")"
  loc="$(cut -d/ -f4 <<<"${path}")"
  
  response=$(curl -s -w "\n%{http_code}" -m 30 -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" "https://${loc}-aiplatform.googleapis.com/v1beta1/${path}")
  code=$(tail -n1 <<< "$response")
  body=$(sed '$d' <<< "$response")

  if [[ "${code}" == "404" ]]; then
    STALE=$((STALE + 1)); echo "STALE  ${path##*/}  ${where}"
    if [[ "${where}" == "IAP V1 "* ]]; then
      echo "       remove with: getIamPolicy and setIamPolicy on the IAP resource iap_web/agentRegistry/${where##* on } (remove the member)"
    elif [[ "${where}" == roles/* ]]; then
      echo "       remove with: gcloud projects remove-iam-policy-binding ${PROJECT} --member='${member}' --role='${where}' --condition=None"
    fi
  elif [[ "${code}" == "200" ]]; then
    LIVE=$((LIVE + 1))
    echo "live   ${path##*/}  ${where}"
    if [[ "${HAS_GATEWAYS}" == "true" ]] && [[ "${CHECKED_GW}" != *" ${path##*/} "* ]]; then
      CHECKED_GW+="${path##*/} "
      egress_gw=$(jq -r '.spec.deploymentSpec.agentGatewayConfig.agentToAnywhereConfig.agentGateway // .agentGatewayConfig.agentToAnywhereConfig.agentGateway // empty' <<< "${body}")
      ingress_gw=$(jq -r '.spec.deploymentSpec.agentGatewayConfig.clientToAgentConfig.agentGateway // .agentGatewayConfig.clientToAgentConfig.agentGateway // empty' <<< "${body}")
      if [[ -z "${egress_gw}" ]] && [[ -z "${ingress_gw}" ]]; then
        MISSING_GW=$((MISSING_GW + 1))
        echo "WARN   ${path##*/}  missing egress or ingress gateway bindings"
      fi
    fi
  else
    echo "ERROR  ${path##*/}  ${where}  (HTTP ${code}, not counted)"
  fi
done <<<"${PRINCIPALS}"

if [[ "${STALE}" -gt 0 ]] || [[ "${MISSING_GW}" -gt 0 ]]; then
  echo "DOCTOR: STALE (${STALE} grants name deleted agents, ${MISSING_GW} live agents lack gateway bindings). Remove each stale grant after review."
else
  echo "DOCTOR: CLEAN (${LIVE} grants name live agents)"
fi
