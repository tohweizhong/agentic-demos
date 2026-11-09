#!/usr/bin/env bash
# Read-only discovery of an existing project (lateral path, phase 1).
# Lists every agent, MCP server, gateway, and access control in the project and
# region, not only the starter pack resources, and shows which tier controls
# cover each one. Writes JSON to stdout, or a Markdown report with --markdown.
#
#   scripts/discover.sh --project PROJECT_ID --region REGION [--prefix PREFIX] [--markdown]
#
# It makes no change. It stops with status ERROR when it cannot read the project,
# so that a failed call is never shown as a fact.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq curl

PROJECT=""; REGION=""; PREFIX=""; MD="false"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --markdown) MD="true"; shift ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
  esac
done
[[ -n "${PROJECT}" && -n "${REGION}" ]] || { echo "ERROR: --project and --region are required." >&2; exit 2; }

TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"
NUMBER="$(gcloud projects describe "${PROJECT}" --format='value(projectNumber)' 2>/dev/null || true)"
if [[ -z "${TOKEN}" || -z "${NUMBER}" ]]; then
  jq -n --arg p "${PROJECT}" '{status:"ERROR", project:$p, error:"gcloud cannot read the project (no account, no token, or no access). No facts were collected."}'
  exit 1
fi
L="projects/${PROJECT}/locations/${REGION}"
ERRS="$(mktemp)"
get() {  # get URL -> JSON body, or {} and an error line
  local body code
  body="$(curl -s -m 30 -w '\n%{http_code}' -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" "$1")"
  code="${body##*$'\n'}"; body="${body%$'\n'*}"
  if [[ "${code}" != "200" ]]; then echo "$1 HTTP ${code}" >> "${ERRS}"; echo '{}'; else echo "${body}"; fi
}

AGENTS="$(get "https://${REGION}-aiplatform.googleapis.com/v1beta1/${L}/reasoningEngines?pageSize=100" | jq '[.reasoningEngines[]? | {
  name: (.name | split("/") | last), display_name: .displayName,
  effective_identity: (.spec.effectiveIdentity // empty),
  identity_type: (.spec.identityType // "SERVICE_ACCOUNT"),
  egress_gateway: (.spec.deploymentSpec.agentGatewayConfig.agentToAnywhereConfig.agentGateway // .spec.agentGatewayConfig.agentToAnywhereConfig.agentGateway // null),
  ingress_gateway: (.spec.deploymentSpec.agentGatewayConfig.clientToAgentConfig.agentGateway // .spec.agentGatewayConfig.clientToAgentConfig.agentGateway // null),
  create_time: .createTime }]')"
GATEWAYS="$(get "https://networkservices.googleapis.com/v1/${L}/agentGateways" | jq '[.agentGateways[]? | {name: (.name | split("/") | last), type: (if .agentToAnywhereConfig then "AGENT_TO_ANYWHERE (egress)" elif .clientToAgentConfig then "CLIENT_TO_AGENT (ingress)" else (.protocols // [] | join(",")) end)}]')"
EXTS="$(get "https://networkservices.googleapis.com/v1beta1/${L}/authzExtensions" | jq '[.authzExtensions[]? | {name: (.name | split("/") | last), service: .service, iap_policy_version: (.metadata.iapPolicyVersion // null), mode: (.metadata.iamEnforcementMode // "ENFORCE (default)")}]')"
REG="$(get "https://agentregistry.googleapis.com/v1alpha/${L}/services?pageSize=200" | jq '[.services[]? | {name: (.name | split("/") | last), kind: (if .mcpServerSpec then "MCP server" elif .endpointSpec then "endpoint" else "service" end), url: (.interfaces[0].url // .endpointSpec.url // null)}]')"
RUN="$(get "https://${REGION}-run.googleapis.com/v2/${L}/services" | jq '[.services[]? | {name: (.name | split("/") | last), url: .uri, functional_type: (.annotations["run.googleapis.com/functional-type"] // .labels["functional-type"] // null)}]')"
APOL="$(get "https://iam.googleapis.com/v3/projects/${PROJECT}/locations/global/accessPolicies" | jq '[.accessPolicies[]? | {name: (.name | split("/") | last), rules: ([.details.rules[]? | {effect, principals: (.principals | length), condition: (.conditions["iap.googleapis.com"].expression // null)}])}]')"
PBIND="$(get "https://iam.googleapis.com/v3/projects/${PROJECT}/locations/global/policyBindings" | jq '[.policyBindings[]? | {name: (.name | split("/") | last), policy: (.policy | split("/") | last)}]')"
MA="$(get "https://modelarmor.${REGION}.rep.googleapis.com/v1/${L}/templates" | jq '[.templates[]? | .name | split("/") | last]')"

# MCP servers on Cloud Run that are not in the registry (match by URL host).
UNREG="$(jq -n --argjson run "${RUN}" --argjson reg "${REG}" '[ $run[] | select(.url as $u | ($reg | map(.url // "" | test(($u // "~") | sub("^https://";""); "i")) | any) | not) | .name ]')"

ERRORS="$(jq -R -s 'split("\n") | map(select(length>0))' < "${ERRS}")"; rm -f "${ERRS}"
STATUS="$(jq -n --argjson e "${ERRORS}" 'if ($e|length)>0 then "PARTIAL" else "OK" end')"

REPORT="$(jq -n --arg project "${PROJECT}" --arg number "${NUMBER}" --arg region "${REGION}" --arg prefix "${PREFIX}" \
  --argjson agents "${AGENTS}" --argjson gateways "${GATEWAYS}" --argjson exts "${EXTS}" --argjson reg "${REG}" \
  --argjson run "${RUN}" --argjson apol "${APOL}" --argjson pbind "${PBIND}" --argjson ma "${MA}" --argjson unreg "${UNREG}" \
  --argjson errors "${ERRORS}" --argjson status "${STATUS}" '
  def sp($n): ($prefix != "" and (($n // "") | startswith($prefix + "-")));
  ($agents | map(. + {starter_pack: sp(.display_name)})) as $agents
  | ($unreg | map(select(sp(.) | not))) as $unreg
  | ([$agents[] | select(.starter_pack | not)]) as $ext
  | {
  status: $status, project: $project, project_number: $number, region: $region, starter_pack_prefix: $prefix,
  summary: {
    agents: ($agents|length), existing_agents_not_from_starter_pack: ($ext|length),
    agents_without_agent_identity: ([$agents[] | select(.identity_type != "AGENT_IDENTITY")] | length),
    agents_without_egress_gateway: ([$agents[] | select(.egress_gateway == null)] | length),
    agents_without_ingress_gateway: ([$agents[] | select(.ingress_gateway == null)] | length),
    cloud_run_services_not_in_registry: ($unreg|length),
    registry_entries: ($reg|length), gateways: ($gateways|length), access_policies: ($apol|length)
  },
  lateral_steps: {
    tier1: [$ext[] | select(.identity_type != "AGENT_IDENTITY") | "Move agent \(.display_name // .name) to AGENT_IDENTITY (new principal) and grant its roles"],
    tier2: [$unreg[] | "Register Cloud Run service \(.) in Agent Registry if it is an MCP server or a tool endpoint"],
    tier3: [$ext[] | select(.egress_gateway == null) | "Bind agent \(.display_name // .name) to the egress gateway and add IAP rules for its principal (DRY_RUN first)"],
    tier5: [$ext[] | select(.ingress_gateway == null) | "Bind agent \(.display_name // .name) to the ingress gateway and move its clients to the gateway"]
  },
  agents: $agents, gateways: $gateways, authz_extensions: $exts, registry: $reg, cloud_run: $run,
  access_policies: $apol, policy_bindings: $pbind, model_armor_templates: $ma, errors: $errors }')"

if [[ "${MD}" != "true" ]]; then echo "${REPORT}"; exit 0; fi
jq -r '
  "# Discovery: \(.project) (\(.region))\n\nStatus: \(.status). Read-only. Errors: \(.errors|length).\n",
  "| Item | Count |", "|---|---|",
  (.summary | to_entries[] | "| \(.key | gsub("_";" ")) | \(.value) |"),
  "\n## Agents\n", "| Agent | Starter pack | Identity | Egress gateway | Ingress gateway |", "|---|---|---|---|---|",
  (.agents[] | "| \(.display_name // .name) (`\(.name)`) | \(if .starter_pack then "yes" else "no" end) | \(.identity_type) | \(.egress_gateway // "none" | split("/") | last) | \(.ingress_gateway // "none" | split("/") | last) |"),
  "\n## Gateways and authz extensions\n",
  (.gateways[] | "- Gateway `\(.name)`: \(.type)"),
  (.authz_extensions[] | "- Extension `\(.name)`: \(.service), IAP policy \(.iap_policy_version // "-"), mode \(.mode)"),
  "\n## Agent Registry\n", (.registry[] | "- \(.kind) `\(.name)` \(.url // "")"),
  "\n## Cloud Run services\n", (.cloud_run[] | "- `\(.name)` \(.url)"),
  "\n## Lateral steps for each tier (existing resources only; the starter pack governs its own resources with the vertical path)\n",
  (.lateral_steps | to_entries[] | "### \(.key)\n", (if (.value|length)==0 then "- Nothing to do." else (.value[] | "- \(.)") end), ""),
  (if (.errors|length)>0 then "## Errors (facts not collected)\n", (.errors[] | "- \(.)") else empty end)
' <<<"${REPORT}"
