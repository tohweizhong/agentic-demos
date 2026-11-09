#!/usr/bin/env bash
# Read-only posture check (backlog item 12, first part): finds stale grants.
# A stale grant names the principal of an agent that no longer exists. Deleting
# an agent does not delete its IAM bindings (Agent Identity lifecycle rule).
#
#   scripts/doctor.sh --project PROJECT_ID
#
# It checks the project allow policy and the IAP access policies (IAM v3). It does
# not check IAP policy V1 grants on iap_web resources or service account policies. It
# prints one line at the end: DOCTOR: CLEAN (...) or DOCTOR: STALE (...).
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq curl

PROJECT=""
while [[ $# -gt 0 ]]; do
  case "$1" in --project) PROJECT="$2"; shift 2 ;; *) echo "ERROR: unknown argument $1" >&2; exit 2 ;; esac
done
[[ -n "${PROJECT}" ]] || { echo "ERROR: --project is required." >&2; exit 2; }
TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"
[[ -n "${TOKEN}" ]] || { echo "DOCTOR: ERROR (gcloud has no token)"; exit 1; }
H=(-s -m 30 -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}")

IAM="$(gcloud projects get-iam-policy "${PROJECT}" --format=json 2>/dev/null)" || { echo "DOCTOR: ERROR (cannot read the project IAM policy)"; exit 1; }
APOL="$(curl "${H[@]}" "https://iam.googleapis.com/v3/projects/${PROJECT}/locations/global/accessPolicies")"

# Agent principals that the policies name: principal://.../reasoningEngines/<ID>
PRINCIPALS="$( { jq -r '.bindings[]? | .role as $r | .members[]? | select(test("reasoningEngines/")) | "\(.)\t\($r)"' <<<"${IAM}";
  jq -r '.accessPolicies[]? | (.name | split("/") | last) as $p | .details.rules[]? | .principals[]? | select(test("reasoningEngines/")) | "\(.)\taccess policy \($p)"' <<<"${APOL}"; } | sort -u)"
if [[ -z "${PRINCIPALS}" ]]; then echo "DOCTOR: CLEAN (no agent principal is named in the project allow policy or the IAP access policies)"; exit 0; fi

STALE=0; LIVE=0; CHECKED=""
while IFS=$'\t' read -r member where; do
  path="$(sed -E 's#.*/resources/aiplatform/(projects/[^/]+/locations/[^/]+/reasoningEngines/[0-9]+).*#\1#' <<<"${member}")"
  loc="$(cut -d/ -f4 <<<"${path}")"
  code="$(curl -s -o /dev/null -w '%{http_code}' -m 30 -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" "https://${loc}-aiplatform.googleapis.com/v1/${path}")"
  if [[ "${code}" == "404" ]]; then
    STALE=$((STALE + 1)); echo "STALE  ${path##*/}  ${where}"
    if [[ "${where}" == roles/* ]]; then
      echo "       remove with: gcloud projects remove-iam-policy-binding ${PROJECT} --member='${member}' --role='${where}' --condition=None"
    fi
  elif [[ "${code}" == "200" ]]; then
    LIVE=$((LIVE + 1)); echo "live   ${path##*/}  ${where}"
  else
    echo "ERROR  ${path##*/}  ${where}  (HTTP ${code}, not counted)"
  fi
done <<<"${PRINCIPALS}"

if [[ "${STALE}" -gt 0 ]]; then
  echo "DOCTOR: STALE (${STALE} grants name deleted agents, ${LIVE} name live agents). Remove each stale grant with Terraform or gcloud after review."
else
  echo "DOCTOR: CLEAN (${LIVE} grants name live agents)"
fi
