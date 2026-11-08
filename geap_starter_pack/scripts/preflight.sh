#!/usr/bin/env bash
# Read-only preflight scan for the GEAP starter pack mini build.
#
# Checks a target project before any change and writes a JSON go or no-go report
# to stdout (and optionally to --out FILE).
#
# Usage:
#   scripts/preflight.sh [--project PROJECT_ID] [--region REGION] [--prefix PREFIX] [--out FILE]
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq curl

PROJECT=""
REGION=""
PREFIX="geap"
OUT_FILE=""

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
    --out)
      OUT_FILE="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 [--project PROJECT_ID] [--region REGION] [--prefix PREFIX] [--out FILE]" >&2
      exit 2
      ;;
  esac
done

TFVARS="${TF_DIR}/terraform.tfvars"
tfvars_val() {
  local key="$1"
  if [[ -f "${TFVARS}" ]]; then
    sed -n -E "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*\"([^\"]+)\".*/\1/p" "${TFVARS}" | head -n 1
  fi
}

if [[ -z "${PROJECT}" ]]; then
  PROJECT="$(tfvars_val project_id)"
fi
if [[ -z "${REGION}" ]]; then
  REGION="$(tfvars_val region)"
  REGION="${REGION:-us-central1}"
fi
if [[ -z "${PREFIX}" || "${PREFIX}" == "geap" ]]; then
  from_file="$(tfvars_val name_prefix)"
  PREFIX="${from_file:-${PREFIX}}"
fi

tfvars_bool() {
  local key="$1"
  local def="$2"
  local val=""
  if [[ -f "${TFVARS}" ]]; then
    val="$(sed -n -E "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*(true|false).*/\1/p" "${TFVARS}" | head -n 1)"
  fi
  echo "${val:-${def}}"
}

ENABLE_EGRESS="$(tfvars_bool enable_egress_gateway true)"
ENABLE_INGRESS="$(tfvars_bool enable_ingress_gateway false)"
ENABLE_MA="$(tfvars_bool enable_model_armor true)"
NEEDS_MA_ROLES="false"
if [[ "${ENABLE_MA}" == "true" && ( "${ENABLE_EGRESS}" == "true" || "${ENABLE_INGRESS}" == "true" ) ]]; then
  NEEDS_MA_ROLES="true"
fi

if [[ -z "${PROJECT}" ]]; then
  echo "ERROR: Pass --project PROJECT_ID or set project_id in terraform/terraform.tfvars." >&2
  exit 2
fi

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
CALLER="$(gcloud config get-value account 2>/dev/null || true)"
TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"

# 1. Project metadata and parent organization
PROJ_JSON="$(gcloud projects describe "${PROJECT}" --format=json 2>/dev/null || echo "{}")"
PROJECT_NUMBER="$(echo "${PROJ_JSON}" | jq -r '.projectNumber // empty')"
LIFECYCLE_STATE="$(echo "${PROJ_JSON}" | jq -r '.lifecycleState // "UNKNOWN"')"

# 2. Billing status
BILLING_JSON="$(gcloud billing projects describe "${PROJECT}" --format=json 2>/dev/null || echo "{}")"
BILLING_ENABLED="$(echo "${BILLING_JSON}" | jq -r '.billingEnabled // false')"
BILLING_ACCOUNT="$(echo "${BILLING_JSON}" | jq -r '.billingAccountName // empty')"

# 3. Caller IAM roles on the project
IAM_JSON="$(gcloud projects get-iam-policy "${PROJECT}" --format=json 2>/dev/null || echo "{}")"
CALLER_ROLES="$(echo "${IAM_JSON}" | jq -c --arg caller "${CALLER}" '
  [ .bindings[]?
    | select(.members[]? | ascii_downcase | endswith(($caller | ascii_downcase)))
    | .role
  ] | unique
')"
HAS_ADMIN_ROLE="$(echo "${CALLER_ROLES}" | jq 'any(. == "roles/owner" or . == "roles/editor")')"

# Check whether the 3 Model Armor roles on any gcp-sa-dep service agent already exist
EXISTING_MA_ROLES="$(echo "${IAM_JSON}" | jq -c '
  [ .bindings[]?
    | select(.role == "roles/modelarmor.calloutUser" or .role == "roles/modelarmor.user" or .role == "roles/serviceusage.serviceUsageConsumer")
    | select(.members[]? | contains("@gcp-sa-dep.iam.gserviceaccount.com"))
    | .role
  ] | unique
')"
MA_ROLES_COUNT="$(echo "${EXISTING_MA_ROLES}" | jq 'length')"

# 4. Enabled APIs
REQUIRED_APIS=(
  "cloudresourcemanager.googleapis.com"
  "serviceusage.googleapis.com"
  "aiplatform.googleapis.com"
  "agentregistry.googleapis.com"
  "artifactregistry.googleapis.com"
  "cloudbuild.googleapis.com"
  "cloudtrace.googleapis.com"
  "compute.googleapis.com"
  "iam.googleapis.com"
  "iamcredentials.googleapis.com"
  "iap.googleapis.com"
  "logging.googleapis.com"
  "modelarmor.googleapis.com"
  "monitoring.googleapis.com"
  "networksecurity.googleapis.com"
  "networkservices.googleapis.com"
  "orgpolicy.googleapis.com"
  "run.googleapis.com"
  "storage.googleapis.com"
  "telemetry.googleapis.com"
)
REQUIRED_APIS_JSON="$(printf '%s\n' "${REQUIRED_APIS[@]}" | jq -R . | jq -s .)"
ENABLED_APIS_RAW="$(gcloud services list --enabled --project="${PROJECT}" --format="value(config.name)" 2>/dev/null || true)"
ENABLED_APIS_JSON="$(printf '%s\n' "${ENABLED_APIS_RAW}" | sed '/^$/d' | jq -R . | jq -s .)"
MISSING_APIS_JSON="$(jq -c -n --argjson req "${REQUIRED_APIS_JSON}" --argjson en "${ENABLED_APIS_JSON}" '$req - $en')"

# 5. Organization policies (effective)
DRS_LEGACY_JSON="$(gcloud org-policies describe iam.allowedPolicyMemberDomains --project="${PROJECT}" --effective --format=json 2>/dev/null || echo "{}")"
DRS_LEGACY_RESTRICTED="$(echo "${DRS_LEGACY_JSON}" | jq 'any(.spec.rules[]?; (.values.allowedValues // []) | length > 0)')"
DRS_LEGACY_ALLOW_ALL="$(echo "${DRS_LEGACY_JSON}" | jq 'any(.spec.rules[]?; .allowAll == true)')"

DRS_MANAGED_JSON="$(gcloud org-policies describe iam.managed.allowedPolicyMembers --project="${PROJECT}" --effective --format=json 2>/dev/null || echo "{}")"
DRS_MANAGED_ENFORCED="$(echo "${DRS_MANAGED_JSON}" | jq 'any(.spec.rules[]?; .enforce == true)')"

# 6. Existing Terraform state
TF_STATE_COUNT=0
if [[ -f "${TF_DIR}/terraform.tfstate" ]]; then
  TF_STATE_COUNT="$(jq '.resources | length' "${TF_DIR}/terraform.tfstate" 2>/dev/null || echo 0)"
fi

# 7. Existing resources with the same prefix in the target region
GATEWAYS_JSON="[]"
AGENTS_JSON="[]"
MCP_SERVERS_JSON="[]"
ENDPOINTS_JSON="[]"
CLOUD_RUN_JSON="[]"

if [[ -n "${TOKEN}" && -n "${PROJECT_NUMBER}" ]]; then
  GW_RESP="$(curl -s -H "Authorization: Bearer ${TOKEN}" \
    "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/agentGateways" 2>/dev/null || echo "{}")"
  GATEWAYS_JSON="$(echo "${GW_RESP}" | jq -c --arg p "${PREFIX}-" '
    [ .agentGateways[]?.name | select( split("/") | last | startswith($p) ) ]
  ' 2>/dev/null || echo "[]")"

  RE_RESP="$(curl -s -H "Authorization: Bearer ${TOKEN}" \
    "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/reasoningEngines" 2>/dev/null || echo "{}")"
  AGENTS_JSON="$(echo "${RE_RESP}" | jq -c --arg p "${PREFIX}-" '
    [ .reasoningEngines[]? | select((.displayName // "") | startswith($p)) | {name: .name, displayName: .displayName} ]
  ' 2>/dev/null || echo "[]")"

  AR_MCP_RESP="$(curl -s -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
    "https://agentregistry.googleapis.com/v1alpha/projects/${PROJECT}/locations/${REGION}/mcpServers" 2>/dev/null || echo "{}")"
  MCP_SERVERS_JSON="$(echo "${AR_MCP_RESP}" | jq -c --arg p "${PREFIX}-" '
    [ .mcpServers[]? | select((.name | split("/") | last | startswith($p)) or ((.displayName // "") | ascii_downcase | contains("work items"))) | .name ]
  ' 2>/dev/null || echo "[]")"

  AR_EP_RESP="$(curl -s -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
    "https://agentregistry.googleapis.com/v1alpha/projects/${PROJECT}/locations/${REGION}/endpoints" 2>/dev/null || echo "{}")"
  ENDPOINTS_JSON="$(echo "${AR_EP_RESP}" | jq -c '
    [ .endpoints[]?.name ]
  ' 2>/dev/null || echo "[]")"

  CR_RESP="$(gcloud run services list --project="${PROJECT}" --region="${REGION}" --format=json 2>/dev/null || echo "[]")"
  CLOUD_RUN_JSON="$(echo "${CR_RESP}" | jq -c --arg p "${PREFIX}-" '
    [ .[]?.metadata.name | select(startswith($p)) ]
  ' 2>/dev/null || echo "[]")"
fi

LOG_BUCKET_ID="${PREFIX}-agent-audit"
LOG_BUCKET_STATE="$(gcloud logging buckets describe "${LOG_BUCKET_ID}" --location="${REGION}" --project="${PROJECT}" --format="value(lifecycleState)" 2>/dev/null || echo "NOT_FOUND")"
if [[ "${LOG_BUCKET_STATE}" == "NOT_FOUND" ]]; then
  ALT_STATE="$(gcloud logging buckets describe "${PREFIX}-audit" --location="${REGION}" --project="${PROJECT}" --format="value(lifecycleState)" 2>/dev/null || echo "NOT_FOUND")"
  if [[ "${ALT_STATE}" != "NOT_FOUND" ]]; then
    LOG_BUCKET_ID="${PREFIX}-audit"
    LOG_BUCKET_STATE="${ALT_STATE}"
  fi
fi

# 8. Compute blockers and warnings
REPORT="$(jq -n \
  --arg ts "${TIMESTAMP}" \
  --arg project "${PROJECT}" \
  --arg project_number "${PROJECT_NUMBER}" \
  --arg lifecycle "${LIFECYCLE_STATE}" \
  --arg region "${REGION}" \
  --arg prefix "${PREFIX}" \
  --arg caller "${CALLER}" \
  --argjson caller_roles "${CALLER_ROLES}" \
  --argjson has_admin "${HAS_ADMIN_ROLE}" \
  --argjson billing_enabled "${BILLING_ENABLED}" \
  --arg billing_account "${BILLING_ACCOUNT}" \
  --argjson missing_apis "${MISSING_APIS_JSON}" \
  --argjson drs_legacy_restricted "${DRS_LEGACY_RESTRICTED}" \
  --argjson drs_legacy_allow_all "${DRS_LEGACY_ALLOW_ALL}" \
  --argjson drs_managed_enforced "${DRS_MANAGED_ENFORCED}" \
  --argjson existing_ma_roles "${EXISTING_MA_ROLES}" \
  --argjson ma_roles_count "${MA_ROLES_COUNT}" \
  --argjson needs_ma_roles "${NEEDS_MA_ROLES}" \
  --argjson tf_state_count "${TF_STATE_COUNT}" \
  --argjson gateways "${GATEWAYS_JSON}" \
  --argjson agents "${AGENTS_JSON}" \
  --argjson mcp_servers "${MCP_SERVERS_JSON}" \
  --argjson endpoints "${ENDPOINTS_JSON}" \
  --argjson cloud_run "${CLOUD_RUN_JSON}" \
  --arg log_bucket_id "${LOG_BUCKET_ID}" \
  --arg log_bucket_state "${LOG_BUCKET_STATE}" \
  '
  def blockers:
    [
      (if $lifecycle != "ACTIVE" then "Project is not ACTIVE (lifecycleState=" + $lifecycle + ")." else empty end),
      (if ($billing_enabled | not) then "Billing is not enabled on the project." else empty end),
      (if ($has_admin | not) then "Caller does not have roles/owner or roles/editor on the project." else empty end),
      (if $log_bucket_state == "DELETE_REQUESTED" then
        "Log bucket " + $log_bucket_id + " is in DELETE_REQUESTED state (7-day soft-delete lock). Undelete it before apply: gcloud logging buckets undelete " + $log_bucket_id + " --location=" + $region + " --project=" + $project
       else empty end),
      (if ($needs_ma_roles and $drs_legacy_restricted and ($ma_roles_count < 3)) then
        "iam.allowedPolicyMemberDomains restricts members and the 3 Model Armor roles on the gcp-sa-dep service agent are not all present yet. Choose Option B or Option C before terraform apply, or set enable_model_armor = false."
       else empty end)
    ];
  def warnings:
    [
      (if ($missing_apis | length) > 0 then
        (($missing_apis | length | tostring) + " required APIs are not enabled yet. Terraform will enable them during apply.")
       else empty end),
      (if ($drs_legacy_restricted and ($ma_roles_count == 3)) then
        "iam.allowedPolicyMemberDomains is active, but all 3 Model Armor roles on the gcp-sa-dep service agent are already present."
       else empty end),
      (if ($tf_state_count == 0 and $log_bucket_state == "ACTIVE") then
        "Log bucket " + $log_bucket_id + " already exists (ACTIVE) while terraform.tfstate is empty. Import it before apply: terraform -chdir=terraform import google_logging_project_bucket_config.audit projects/" + $project + "/locations/" + $region + "/buckets/" + $log_bucket_id
       else empty end),
      (if ($tf_state_count == 0 and (($gateways | length) > 0 or ($agents | length) > 0 or ($cloud_run | length) > 0)) then
        "Existing GEAP resources exist in the project, but local terraform.tfstate is empty."
       else empty end)
    ];
  {
    timestamp: $ts,
    status: (if (blockers | length) == 0 then "GO" else "NO_GO" end),
    project: {
      project_id: $project,
      project_number: $project_number,
      lifecycle_state: $lifecycle,
      region: $region,
      name_prefix: $prefix
    },
    caller: {
      account: $caller,
      roles: $caller_roles,
      has_owner_or_editor: $has_admin
    },
    billing: {
      enabled: $billing_enabled,
      billing_account: $billing_account
    },
    apis: {
      missing_count: ($missing_apis | length),
      missing: $missing_apis
    },
    org_policies: {
      iam_allowedPolicyMemberDomains_restricted: $drs_legacy_restricted,
      iam_allowedPolicyMemberDomains_allow_all: $drs_legacy_allow_all,
      iam_managed_allowedPolicyMembers_enforced: $drs_managed_enforced,
      existing_model_armor_roles_on_gcp_sa_dep: $existing_ma_roles
    },
    existing_resources: {
      terraform_state_resource_count: $tf_state_count,
      agent_gateways: $gateways,
      reasoning_engines: $agents,
      agent_registry_mcp_servers: $mcp_servers,
      agent_registry_endpoints: $endpoints,
      cloud_run_services: $cloud_run,
      log_bucket: {
        bucket_id: $log_bucket_id,
        lifecycle_state: $log_bucket_state
      }
    },
    blockers: blockers,
    warnings: warnings
  }
')"

if [[ -n "${OUT_FILE}" ]]; then
  printf '%s\n' "${REPORT}" > "${OUT_FILE}"
fi

printf '%s\n' "${REPORT}"
STATUS="$(echo "${REPORT}" | jq -r '.status')"
if [[ "${STATUS}" != "GO" ]]; then
  exit 1
fi
