#!/usr/bin/env bash
# Read-only preflight scan for the agent governance starter pack mini build.
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
ALLOW_GMM="$(tfvars_bool allow_google_managed_members false)"
NEEDS_MA_ROLES="false"
if [[ "${ENABLE_MA}" == "true" && ( "${ENABLE_EGRESS}" == "true" || "${ENABLE_INGRESS}" == "true" ) ]]; then
  NEEDS_MA_ROLES="true"
fi

if [[ -z "${PROJECT}" ]]; then
  echo "ERROR: Pass --project PROJECT_ID or set project_id in terraform/terraform.tfvars." >&2
  exit 2
fi

TIMESTAMP="$(TZ=Asia/Singapore date +"%Y-%m-%dT%H:%M:%S+08:00")"
CALLER="$(gcloud config get-value account 2>/dev/null || true)"
TOKEN="$(gcloud auth print-access-token 2>/dev/null || true)"

# 1. Project metadata and parent organization
PROJ_JSON="$(gcloud projects describe "${PROJECT}" --format=json 2>/dev/null || echo "{}")"
PROJECT_NUMBER="$(echo "${PROJ_JSON}" | jq -r '.projectNumber // empty')"
LIFECYCLE_STATE="$(echo "${PROJ_JSON}" | jq -r '.lifecycleState // "UNKNOWN"')"

# Stop with a clear error when gcloud cannot read the project. Without this
# check, each failed gcloud call looks like a project fact (not ACTIVE, no
# billing, no APIs), and the report is false.
if [[ -z "${CALLER}" || -z "${TOKEN}" || -z "${PROJECT_NUMBER}" ]]; then
  REASON="gcloud cannot read project ${PROJECT}."
  [[ -z "${CALLER}" ]] && REASON="${REASON} No active gcloud account (run: gcloud auth login)."
  [[ -z "${TOKEN}" ]] && REASON="${REASON} No gcloud access token."
  [[ -n "${CALLER}" && -n "${TOKEN}" ]] && REASON="${REASON} The project does not exist, or ${CALLER} has no access to it."
  jq -n --arg ts "${TIMESTAMP}" --arg project "${PROJECT}" --arg region "${REGION}" --arg prefix "${PREFIX}" \
    --arg caller "${CALLER}" --arg reason "${REASON}" '{
      timestamp: $ts,
      status: "ERROR",
      project: {project_id: $project, region: $region, name_prefix: $prefix},
      caller: {account: $caller},
      blockers: [$reason + " The other checks did not run, so this report has no project facts."],
      warnings: []
    }'
  exit 1
fi

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

# Check the 3 Model Armor roles on the service agent of THIS egress gateway. Each
# gateway has its own tenant service agent (service-<TENANT_NUMBER>@gcp-sa-dep).
# Roles on another gcp-sa-dep service agent (for example from an earlier gateway)
# do not count (rehearsal problem 39, 12 Nov 2026). Before the gateway exists,
# the script cannot tell which service agent the gateway will get.
MA_SERVICE_AGENT="$(gcloud network-services agent-gateways describe "${PREFIX}-egress" --location="${REGION}" --project="${PROJECT}" \
  --format='value(agentGatewayCard.serviceExtensionsServiceAccount)' 2>/dev/null || true)"
if [[ -n "${MA_SERVICE_AGENT}" ]]; then
  EXISTING_MA_ROLES="$(echo "${IAM_JSON}" | jq -c --arg m "serviceAccount:${MA_SERVICE_AGENT}" '
    [ .bindings[]?
      | select(.role == "roles/modelarmor.calloutUser" or .role == "roles/modelarmor.user" or .role == "roles/serviceusage.serviceUsageConsumer")
      | select(.members | index($m))
      | .role
    ] | unique
  ')"
else
  EXISTING_MA_ROLES="[]"
fi
MA_ROLES_COUNT="$(echo "${EXISTING_MA_ROLES}" | jq 'length')"
OTHER_SA_DEP_ROLES="$(echo "${IAM_JSON}" | jq -c --arg m "serviceAccount:${MA_SERVICE_AGENT:-none}" '
  [ .bindings[]?
    | select(.role == "roles/modelarmor.calloutUser" or .role == "roles/modelarmor.user" or .role == "roles/serviceusage.serviceUsageConsumer")
    | .members[]? | select(contains("@gcp-sa-dep.iam.gserviceaccount.com") and . != $m)
  ] | unique
')"

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

# 7b. Credentials that Terraform will use (Application Default Credentials).
# gcloud and Terraform look for ADC in different places. In Cloud Shell, gcloud
# keeps its files in $CLOUDSDK_CONFIG, but the Terraform provider reads
# $GOOGLE_APPLICATION_CREDENTIALS or ~/.config/gcloud only, and else asks the
# metadata server (found in the manual rehearsal on 09 Nov 2026).
TF_ADC_SOURCE="none"
TF_ADC_FIX=""
if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  if [[ -f "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
    TF_ADC_SOURCE="GOOGLE_APPLICATION_CREDENTIALS"
  else
    TF_ADC_SOURCE="missing_file"
    TF_ADC_FIX="CLOUDSDK_CONFIG=\"$(dirname "${GOOGLE_APPLICATION_CREDENTIALS}")\" gcloud auth application-default login"
  fi
elif [[ -f "${HOME}/.config/gcloud/application_default_credentials.json" ]]; then
  TF_ADC_SOURCE="well_known_file"
elif [[ -n "${CLOUDSDK_CONFIG:-}" && -f "${CLOUDSDK_CONFIG}/application_default_credentials.json" ]]; then
  TF_ADC_SOURCE="cloudsdk_config_only"
  TF_ADC_FIX="export GOOGLE_APPLICATION_CREDENTIALS=\"${CLOUDSDK_CONFIG}/application_default_credentials.json\""
elif curl -s -m 3 -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email" 2>/dev/null | grep -q "@"; then
  TF_ADC_SOURCE="metadata_server"
fi
if [[ "${TF_ADC_SOURCE}" == "none" ]]; then
  if [[ -n "${CLOUDSDK_CONFIG:-}" ]]; then
    # Cloud Shell: the login writes the file to $CLOUDSDK_CONFIG of this shell.
    TF_ADC_FIX="gcloud auth application-default login && export GOOGLE_APPLICATION_CREDENTIALS=\"${CLOUDSDK_CONFIG}/application_default_credentials.json\""
  else
    TF_ADC_FIX="gcloud auth application-default login"
  fi
fi

# 7c. Free disk space in terraform/, so that terraform.tfstate is not cut short.
# -1 means that df gave no number. The report then has a warning, not a blocker.
DISK_FREE_MB="$(df -Pm "${TF_DIR}" 2>/dev/null | awk 'NR==2 {print $4}')"
if [[ ! "${DISK_FREE_MB}" =~ ^[0-9]+$ ]]; then
  DISK_FREE_MB="-1"
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
  --arg ma_service_agent "${MA_SERVICE_AGENT}" \
  --argjson other_sa_dep_members "${OTHER_SA_DEP_ROLES}" \
  --argjson ma_roles_count "${MA_ROLES_COUNT}" \
  --argjson needs_ma_roles "${NEEDS_MA_ROLES}" \
  --argjson allow_gmm "${ALLOW_GMM}" \
  --argjson tf_state_count "${TF_STATE_COUNT}" \
  --argjson gateways "${GATEWAYS_JSON}" \
  --argjson agents "${AGENTS_JSON}" \
  --argjson mcp_servers "${MCP_SERVERS_JSON}" \
  --argjson endpoints "${ENDPOINTS_JSON}" \
  --argjson cloud_run "${CLOUD_RUN_JSON}" \
  --arg log_bucket_id "${LOG_BUCKET_ID}" \
  --arg log_bucket_state "${LOG_BUCKET_STATE}" \
  --arg tf_adc_source "${TF_ADC_SOURCE}" \
  --arg tf_adc_fix "${TF_ADC_FIX}" \
  --argjson disk_free_mb "${DISK_FREE_MB}" \
  '
  def blockers:
    [
      (if $lifecycle != "ACTIVE" then "Project is not ACTIVE (lifecycleState=" + $lifecycle + ")." else empty end),
      (if ($billing_enabled | not) then "Billing is not enabled on the project." else empty end),
      (if ($has_admin | not) then "Caller does not have roles/owner or roles/editor on the project." else empty end),
      (if $log_bucket_state == "DELETE_REQUESTED" then
        "Log bucket " + $log_bucket_id + " is in DELETE_REQUESTED state (7-day soft-delete lock). Undelete it before apply: gcloud logging buckets undelete " + $log_bucket_id + " --location=" + $region + " --project=" + $project
       else empty end),
      (if ($disk_free_mb >= 0 and $disk_free_mb < 250) then
        "Free disk space in terraform/ is " + ($disk_free_mb | tostring) + " MB (< 250 MB). Free disk space before running Terraform so terraform.tfstate is not truncated."
       else empty end),
      (if $tf_adc_source == "none" then
        "Terraform has no credentials: no GOOGLE_APPLICATION_CREDENTIALS file, no ~/.config/gcloud ADC file, and no metadata server account. Run this in the same shell before terraform or agy: " + $tf_adc_fix
       elif $tf_adc_source == "missing_file" then
        "GOOGLE_APPLICATION_CREDENTIALS points to a file that does not exist. Terraform does not fall back to the metadata server when this variable is set. Run: " + $tf_adc_fix
       elif $tf_adc_source == "cloudsdk_config_only" then
        "Terraform cannot find the ADC file. It is only in $CLOUDSDK_CONFIG (Cloud Shell). Run this in the same shell before terraform or agy: " + $tf_adc_fix
       else empty end),
      (if ($needs_ma_roles and $drs_legacy_restricted and ($ma_roles_count < 3) and ($allow_gmm | not)) then
        "iam.allowedPolicyMemberDomains restricts members and the 3 Model Armor roles on the gcp-sa-dep service agent of the egress gateway are not all present yet (or the gateway does not exist yet). Choose Approach 1, 2, or 3 in GUIDE Section 3 before terraform apply, or set enable_model_armor = false."
       else empty end)
    ];
  def warnings:
    [
      (if $disk_free_mb < 0 then
        "Could not read the free disk space in terraform/ with df. Check it before terraform apply."
       else empty end),
      (if ($disk_free_mb >= 250 and $disk_free_mb < 1024) then
        "Free disk space in terraform/ is " + ($disk_free_mb | tostring) + " MB (< 1024 MB). Free up space soon."
       else empty end),
      (if ($needs_ma_roles and $drs_legacy_restricted and ($ma_roles_count < 3) and $allow_gmm) then
        "allow_google_managed_members = true: Terraform sets a temporary project exception to iam.allowedPolicyMemberDomains for the 3 Model Armor roles (Approach 2). Set it back to false and apply again after the roles exist."
       else empty end),
      (if ($missing_apis | length) > 0 then
        (($missing_apis | length | tostring) + " required APIs are not enabled yet. Terraform will enable them during apply.")
       else empty end),
      (if ($drs_legacy_restricted and ($ma_roles_count == 3)) then
        "iam.allowedPolicyMemberDomains is active, but all 3 Model Armor roles on the service agent of the egress gateway (" + $ma_service_agent + ") are already present."
       else empty end),
      (if ($needs_ma_roles and ($ma_service_agent == "")) then
        "The egress gateway does not exist yet, so the script cannot tell which gcp-sa-dep service agent it will use. Roles on other gcp-sa-dep service agents do not count."
       else empty end),
      (if ($needs_ma_roles and (($other_sa_dep_members | length) > 0)) then
        "Model Armor roles exist on other gcp-sa-dep service agents (" + ($other_sa_dep_members | join(", ")) + "). They are not the service agent of this gateway."
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
    disk_free_mb: $disk_free_mb,
    terraform_credentials: {source: $tf_adc_source},
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
      existing_model_armor_roles_on_gcp_sa_dep: $existing_ma_roles,
      model_armor_service_agent: (if $ma_service_agent == "" then "unknown (no egress gateway yet)" else $ma_service_agent end),
      model_armor_roles_on_other_gcp_sa_dep: $other_sa_dep_members
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
