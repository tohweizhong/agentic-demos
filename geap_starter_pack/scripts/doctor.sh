#!/usr/bin/env bash
# Read-only posture and rogue-agent doctor for the GEAP starter pack.
#
# Inspects the live Google Cloud project and reports:
# 1. Active status of each of the 5 Governance Tiers (PASS, OFF, or DRIFT).
# 2. Every Vertex AI Reasoning Engine in the region, flagging any ungoverned
#    (rogue) agent missing AGENT_IDENTITY, agentToAnywhereConfig, or
#    clientToAgentConfig.
# 3. Live IAP enforcement mode (DRY_RUN vs ENFORCE) on <prefix>-egress-iap-authz.
# 4. Presence of the 3 Model Armor IAM roles on the gcp-sa-dep service agent.
#
# Usage:
#   scripts/doctor.sh [--project PROJECT_ID] [--region REGION] [--prefix PREFIX]
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq curl

PROJECT=""
REGION=""
PREFIX=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    --prefix)
      PREFIX="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 [--project PROJECT_ID] [--region REGION] [--prefix PREFIX]" >&2
      exit 2
      ;;
  esac
done

TFVARS="${TF_DIR}/terraform.tfvars"
tfvars_val() {
  local key="$1"
  if [[ -f "${TFVARS}" ]]; then
    sed -n -E "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*\"?([^\"#[:space:]]+)\"?.*/\1/p" "${TFVARS}" | head -n 1
  fi
}

if [[ -z "${PROJECT}" ]]; then
  PROJECT="$(terraform -chdir="${TF_DIR}" output -raw project_id 2>/dev/null || true)"
fi
if [[ -z "${PROJECT}" ]]; then
  PROJECT="$(tfvars_val project_id)"
fi

if [[ -z "${REGION}" ]]; then
  REGION="$(terraform -chdir="${TF_DIR}" output -raw region 2>/dev/null || true)"
fi
if [[ -z "${REGION}" ]]; then
  REGION="$(tfvars_val region)"
  REGION="${REGION:-us-central1}"
fi

if [[ -z "${PREFIX}" ]]; then
  PREFIX="$(tfvars_val name_prefix)"
  PREFIX="${PREFIX:-geap}"
fi

if [[ -z "${PROJECT}" ]]; then
  echo "ERROR: Pass --project PROJECT_ID or set project_id in terraform/terraform.tfvars." >&2
  exit 2
fi

EXP_T2="$(tfvars_val enable_agent_registry)"
EXP_T2="${EXP_T2:-true}"
EXP_T3="$(tfvars_val enable_egress_gateway)"
EXP_T3="${EXP_T3:-true}"
EXP_T4="$(tfvars_val enable_model_armor)"
EXP_T4="${EXP_T4:-true}"
EXP_T5="$(tfvars_val enable_ingress_gateway)"
EXP_T5="${EXP_T5:-false}"
EXP_IAP_MODE="$(tfvars_val iap_enforcement_mode)"
EXP_IAP_MODE="${EXP_IAP_MODE:-DRY_RUN}"

TOKEN="$(gcloud auth print-access-token)"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Tier 1: Cloud Run MCP server, regional log bucket, and Reasoning Engines
CR_OK="false"
if gcloud run services describe "${PREFIX}-work-items" --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
  CR_OK="true"
fi

LOG_BKT_STATE="$(gcloud logging buckets describe "${PREFIX}-agent-audit" --location="${REGION}" --project="${PROJECT}" --format="value(lifecycleState)" 2>/dev/null || echo "NOT_FOUND")"

RE_RESP="$(curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT}/locations/${REGION}/reasoningEngines" 2>/dev/null || echo "{}")"

# Tier 2: Agent Registry MCP server and Google APIs endpoint (registered via services/)
AR_MCP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
  "https://agentregistry.googleapis.com/v1alpha/projects/${PROJECT}/locations/${REGION}/services/${PREFIX}-work-items")"
AR_EP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
  "https://agentregistry.googleapis.com/v1alpha/projects/${PROJECT}/locations/${REGION}/services/${PREFIX}-google-apis")"

# Tier 3: Egress gateway, IAP authz extension, and IAP authz policy
EG_GW_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
  "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/agentGateways/${PREFIX}-egress")"
IAP_EXT_JSON="$(curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzExtensions/${PREFIX}-egress-iap-authz" 2>/dev/null || echo "{}")"
IAP_EXT_EXISTS="$(echo "${IAP_EXT_JSON}" | jq 'has("name")')"
LIVE_IAP_MODE="$(echo "${IAP_EXT_JSON}" | jq -r 'if (.metadata.iamEnforcementMode // "") == "DRY_RUN" then "DRY_RUN" elif has("name") then "ENFORCE" else "NONE" end')"
IAP_POL_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
  "https://networksecurity.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzPolicies/${PREFIX}-egress-iap-policy")"

# Tier 4: Model Armor templates, authz extension, policies, and 3 gcp-sa-dep IAM bindings
MA_REQ_OK="false"
MA_RESP_OK="false"
if gcloud model-armor templates describe "${PREFIX}-agw-request" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
  MA_REQ_OK="true"
fi
if gcloud model-armor templates describe "${PREFIX}-agw-response" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
  MA_RESP_OK="true"
fi
MA_EXT_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
  "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzExtensions/${PREFIX}-egress-ma-authz")"
MA_EG_POL_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
  "https://networksecurity.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzPolicies/${PREFIX}-egress-ma-policy")"
MA_IN_POL_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
  "https://networksecurity.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzPolicies/${PREFIX}-ingress-ma-policy")"

IAM_JSON="$(gcloud projects get-iam-policy "${PROJECT}" --format=json 2>/dev/null || echo "{}")"
MA_ROLES_JSON="$(echo "${IAM_JSON}" | jq -c '
  [ .bindings[]?
    | select(.role == "roles/modelarmor.calloutUser" or .role == "roles/modelarmor.user" or .role == "roles/serviceusage.serviceUsageConsumer")
    | select(.members[]? | contains("@gcp-sa-dep.iam.gserviceaccount.com"))
    | .role
  ] | unique
')"
MA_ROLES_COUNT="$(echo "${MA_ROLES_JSON}" | jq 'length')"

# Tier 5: Ingress gateway
IN_GW_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
  "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/agentGateways/${PREFIX}-ingress")"

REPORT="$(jq -n \
  --arg ts "${TIMESTAMP}" \
  --arg project "${PROJECT}" \
  --arg region "${REGION}" \
  --arg prefix "${PREFIX}" \
  --argjson exp_t2 "${EXP_T2}" \
  --argjson exp_t3 "${EXP_T3}" \
  --argjson exp_t4 "${EXP_T4}" \
  --argjson exp_t5 "${EXP_T5}" \
  --arg exp_iap_mode "${EXP_IAP_MODE}" \
  --arg live_iap_mode "${LIVE_IAP_MODE}" \
  --argjson cr_ok "${CR_OK}" \
  --arg log_bkt_state "${LOG_BKT_STATE}" \
  --arg ar_mcp_code "${AR_MCP_CODE}" \
  --arg ar_ep_code "${AR_EP_CODE}" \
  --arg eg_gw_code "${EG_GW_CODE}" \
  --argjson iap_ext_exists "${IAP_EXT_EXISTS}" \
  --arg iap_pol_code "${IAP_POL_CODE}" \
  --argjson ma_req_ok "${MA_REQ_OK}" \
  --argjson ma_resp_ok "${MA_RESP_OK}" \
  --arg ma_ext_code "${MA_EXT_CODE}" \
  --arg ma_eg_pol_code "${MA_EG_POL_CODE}" \
  --arg ma_in_pol_code "${MA_IN_POL_CODE}" \
  --argjson ma_roles "${MA_ROLES_JSON}" \
  --argjson ma_roles_count "${MA_ROLES_COUNT}" \
  --arg in_gw_code "${IN_GW_CODE}" \
  --argjson re_resp "${RE_RESP}" \
  '
  def agents_summary:
    [ ($re_resp.reasoningEngines // [])[] |
      {
        name: .name,
        display_name: (.displayName // ""),
        identity_type: (.spec.identityType // "SERVICE_ACCOUNT"),
        egress_gateway: (.spec.deploymentSpec.agentGatewayConfig.agentToAnywhereConfig.agentGateway // ""),
        ingress_gateway: (.spec.deploymentSpec.agentGatewayConfig.clientToAgentConfig.agentGateway // ""),
        missing_controls: [
          (if (.spec.identityType // "") != "AGENT_IDENTITY" then "AGENT_IDENTITY" else empty end),
          (if ($eg_gw_code == "200") and ((.spec.deploymentSpec.agentGatewayConfig.agentToAnywhereConfig.agentGateway // "") == "") then "agentToAnywhereConfig" else empty end),
          (if ($in_gw_code == "200") and ((.spec.deploymentSpec.agentGatewayConfig.clientToAgentConfig.agentGateway // "") == "") then "clientToAgentConfig" else empty end)
        ]
      }
    ];
  def rogue_agents:
    [ agents_summary[] | select((.missing_controls | length) > 0) ];
  def t1_status:
    if ($cr_ok and $log_bkt_state == "ACTIVE" and ((agents_summary | length) > 0) and ([agents_summary[] | select(.identity_type == "AGENT_IDENTITY")] | length) == (agents_summary | length))
    then "PASS" else "DRIFT" end;
  def t2_status:
    if ($exp_t2 | not) and $ar_mcp_code != "200" and $ar_ep_code != "200" then "OFF"
    elif $exp_t2 and $ar_mcp_code == "200" and $ar_ep_code == "200" then "PASS"
    else "DRIFT" end;
  def t3_status:
    if ($exp_t3 | not) and $eg_gw_code != "200" then "OFF"
    elif $exp_t3 and $eg_gw_code == "200" and $iap_ext_exists and $iap_pol_code == "200" and ($live_iap_mode == $exp_iap_mode) then "PASS"
    else "DRIFT" end;
  def t4_status:
    if ($exp_t4 | not) and ($ma_req_ok | not) and ($ma_resp_ok | not) then "OFF"
    elif $exp_t4 and $ma_req_ok and $ma_resp_ok and $ma_ext_code == "200" and ($ma_roles_count == 3)
      and (($exp_t3 | not) or $ma_eg_pol_code == "200")
      and (($exp_t5 | not) or $ma_in_pol_code == "200")
    then "PASS"
    else "DRIFT" end;
  def t5_status:
    if ($exp_t5 | not) and $in_gw_code != "200" then "OFF"
    elif $exp_t5 and $in_gw_code == "200" then "PASS"
    else "DRIFT" end;
  {
    timestamp: $ts,
    project_id: $project,
    region: $region,
    name_prefix: $prefix,
    status: (
      if (t1_status != "DRIFT" and t2_status != "DRIFT" and t3_status != "DRIFT" and t4_status != "DRIFT" and t5_status != "DRIFT" and ((rogue_agents | length) == 0))
      then "PASS" else "DRIFT" end
    ),
    tiers: {
      tier_1_identity_and_runtime: t1_status,
      tier_2_catalog_and_discovery: t2_status,
      tier_3_outbound_access_control: t3_status,
      tier_4_content_safety_model_armor: t4_status,
      tier_5_inbound_client_control: t5_status
    },
    iap_enforcement_mode: {
      configured_in_tfvars: $exp_iap_mode,
      live_on_extension: $live_iap_mode
    },
    model_armor_gcp_sa_dep_roles: {
      count: $ma_roles_count,
      roles: $ma_roles
    },
    agents: {
      total_count: (agents_summary | length),
      rogue_count: (rogue_agents | length),
      all_agents: agents_summary,
      rogue_agents: rogue_agents
    }
  }
')"

printf '%s\n' "${REPORT}"
OVERALL="$(echo "${REPORT}" | jq -r '.status')"
if [[ "${OVERALL}" != "PASS" ]]; then
  exit 1
fi
