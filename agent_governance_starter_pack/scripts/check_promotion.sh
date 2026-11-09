#!/usr/bin/env bash
# Read-only promotion readiness report (backlog item 13). Run it before you
# switch iap_enforcement_mode from DRY_RUN to ENFORCE.
#
#   scripts/check_promotion.sh [--lookback 24h]
#
# It combines two sources:
#   1. Static: the tools that the IAP access policy denies (policies/iap_access_policy.yaml),
#      matched with the MCP tool spec. ENFORCE blocks these tools.
#   2. Logs: IAP Data Access entries in the lookback window with granted=false and
#      dryRun=true. ENFORCE would block these calls.
# Known gap: with IAP policy V2, the IAP log has no entry for MCP tools/call decisions,
# so the logs show only MCP base methods. The static part is then the main evidence.
# Prints one line at the end: PROMOTION: READY (...) or PROMOTION: REVIEW (...).
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq python3

LOOKBACK="24h"
while [[ $# -gt 0 ]]; do
  case "$1" in --lookback) LOOKBACK="$2"; shift 2 ;; *) echo "ERROR: unknown argument $1" >&2; exit 2 ;; esac
done

TFVARS="${TF_DIR}/terraform.tfvars"
val() { [[ -f "${TFVARS}" ]] || return 0; sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*\"\{0,1\}\([^\"#]*\)\"\{0,1\}.*/\1/p" "${TFVARS}" | head -1 | sed 's/[[:space:]]*$//' || true; }
PROJECT="$(val project_id)"; MODE="$(val iap_enforcement_mode)"; EGRESS="$(val enable_egress_gateway)"
[[ -n "${PROJECT}" ]] || { echo "PROMOTION: ERROR (no project_id in terraform.tfvars)"; exit 1; }
if [[ "${EGRESS}" != "true" ]]; then echo "PROMOTION: NOT_APPLICABLE (Tier 3 egress gateway is not enabled, so there is no IAP policy to promote)"; exit 0; fi

DENIED_TOOLS="$(python3 - "${ROOT}/policies/iap_access_policy.yaml" "${ROOT}/mcp-server/tool_spec.json" <<'PY'
import json, re, sys
pol = open(sys.argv[1]).read()
blocks = re.split(r"\n\s*-\s+description:", pol)
deny = set()
for b in blocks:
    if re.search(r"effect:\s*DENY", b):
        deny |= set(re.findall(r"tool\.name\s*==\s*'([^']+)'", b))
spec = {t["name"] for t in json.load(open(sys.argv[2])).get("tools", [])}
print(" ".join(sorted(deny)))
unknown = sorted(deny - spec)
if unknown:
    print("WARN: the policy denies tools that are not in the tool spec: " + ", ".join(unknown), file=sys.stderr)
PY
)"

echo "Project ${PROJECT}, mode ${MODE}, lookback ${LOOKBACK}."
echo "Static: tools that ENFORCE blocks for the reference agent: ${DENIED_TOOLS:-none}"

ENTRIES="$(gcloud logging read "protoPayload.serviceName=\"iap.googleapis.com\" AND protoPayload.authorizationInfo.permission:\"egressViaIAP\"" \
  --project="${PROJECT}" --freshness="${LOOKBACK}" --limit=1000 --format=json 2>/dev/null)" || { echo "PROMOTION: ERROR (cannot read the IAP Data Access log; check gcloud auth and logging.viewer)"; exit 1; }
SUMMARY="$(jq -c '{
  total: length,
  would_block: [ .[] | select(.protoPayload.authorizationInfo[0].granted == false) ] | length,
  tools_call_entries: [ .[] | select(.protoPayload.request.mcp_method == "tools/call") ] | length,
  by_method: (group_by(.protoPayload.request.mcp_method // "none") | map({method: (.[0].protoPayload.request.mcp_method // "none"), count: length}))
}' <<<"${ENTRIES:-[]}")"
echo "Logs: ${SUMMARY}"

WB="$(jq '.would_block' <<<"${SUMMARY}")"; TC="$(jq '.tools_call_entries' <<<"${SUMMARY}")"; TOTAL="$(jq '.total' <<<"${SUMMARY}")"
NOTE=""
[[ "${TC}" -eq 0 ]] && NOTE=" The IAP log has no tools/call entries (known gap with IAP policy V2), so the logs cannot show which tool calls ENFORCE blocks. Use the static list and a test call of each denied tool."
if [[ "${WB}" -gt 0 ]]; then
  echo "PROMOTION: REVIEW (${WB} logged decisions would be blocked in ENFORCE; denied tools: ${DENIED_TOOLS:-none}).${NOTE}"
elif [[ "${TOTAL}" -eq 0 ]]; then
  echo "PROMOTION: REVIEW (no IAP decisions in the last ${LOOKBACK}; run the agent in DRY_RUN first; denied tools: ${DENIED_TOOLS:-none}).${NOTE}"
else
  echo "PROMOTION: READY (no logged decision would be blocked; ENFORCE blocks only the denied tools: ${DENIED_TOOLS:-none}).${NOTE}"
fi
