#!/usr/bin/env bash
# Read-only posture check (backlog item 12). Finds stale grants and missing gateway bindings.
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
    p=$(jq -r '.bindings[]? | .role as $r | .members[]? | select(test("reasoningEngines/")) | "\(.)\t\($r) on \(env.sa)"' <<<"${sa_iam}")
    if [[ -n "${p}" ]]; then
      SA_PRINCIPALS+="${p}
"
    fi
  fi
done

PRINCIPALS="$( { jq -r '.bindings[]? | .role as $r | .members[]? | select(test("reasoningEngines/")) | "\(.)\t\($r)"' <<<"${IAM}";
  jq -r '.accessPolicies[]? | (.name | split("/") | last) as $p | .details.rules[]? | .principals[]? | select(test("reasoningEngines/")) | "\(.)\taccess policy \($p)"' <<<"${APOL}";
  [[ -n "${SA_PRINCIPALS}" ]] && echo "${SA_PRINCIPALS}";
  } | grep -v '^$' | sort -u || true)"

HAS_GATEWAYS="false"
if gcloud network-services agent-gateways list --location="${REGION}" --project="${PROJECT}" --format="value(name)" 2>/dev/null | grep -q .; then
  HAS_GATEWAYS="true"
fi

if [[ -z "${PRINCIPALS}" ]]; then echo "DOCTOR: CLEAN (no agent principal is named in the project allow policy or the IAP access policies)"; exit 0; fi

STALE=0; LIVE=0; MISSING_GW=0
while IFS=$'\t' read -r member where; do
  path="$(sed -E 's#.*/resources/aiplatform/(projects/[^/]+/locations/[^/]+/reasoningEngines/[0-9]+).*#\1#' <<<"${member}")"
  loc="$(cut -d/ -f4 <<<"${path}")"
  
  response=$(curl -s -w "\n%{http_code}" -m 30 -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" "https://${loc}-aiplatform.googleapis.com/v1/${path}")
  code=$(tail -n1 <<< "$response")
  body=$(sed '$d' <<< "$response")

  if [[ "${code}" == "404" ]]; then
    STALE=$((STALE + 1)); echo "STALE  ${path##*/}  ${where}"
    if [[ "${where}" == roles/* ]]; then
      echo "       remove with: gcloud projects remove-iam-policy-binding ${PROJECT} --member='${member}' --role='${where}' --condition=None"
    fi
  elif [[ "${code}" == "200" ]]; then
    LIVE=$((LIVE + 1))
    echo "live   ${path##*/}  ${where}"
    if [[ "${HAS_GATEWAYS}" == "true" ]]; then
      egress_gw=$(jq -r '.agentGatewayConfig.agentToAnywhereConfig.agentGateway // empty' <<< "${body}")
      ingress_gw=$(jq -r '.agentGatewayConfig.clientToAgentConfig.agentGateway // empty' <<< "${body}")
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
