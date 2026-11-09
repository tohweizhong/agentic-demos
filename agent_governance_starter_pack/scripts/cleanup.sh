#!/usr/bin/env bash
# Resets an agent governance starter pack project cleanly.
#
# 1. Reads PROJECT, REGION, and PREFIX from Terraform outputs or terraform.tfvars.
# 2. Runs `terraform destroy` when Terraform state contains resources.
# 3. Sweeps the <prefix>-* resources that are not in the Terraform state. The
#    sweep deletes authz policies first, waits for each delete to finish, then
#    deletes the gateways and the authz extensions.
# 4. Protects against the 7-day Cloud Logging bucket soft-delete lock by
#    undeleting the audit bucket by default (--keep-log-bucket), or deletes it
#    when --purge-all is passed.
# 5. Project-wide steps (the Cloud Build source bucket, all gcp-sa-dep Model
#    Armor role bindings, and the project-level domain restriction overrides)
#    only report what they find, unless --include-project-wide is passed.
#    Use that flag only in a project that holds the starter pack and nothing else.
#
# The script exits with code 1 if any delete fails.
#
# Usage:
#   scripts/cleanup.sh [--project PROJECT_ID] [--region REGION] [--prefix PREFIX]
#                      [--keep-log-bucket | --purge-all] [--include-project-wide]
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need terraform gcloud jq curl

PROJECT=""
REGION=""
PREFIX=""
LOG_BUCKET_MODE="keep"
INCLUDE_PROJECT_WIDE="false"
FAILURES=0

usage() {
  echo "Usage: $0 [--project PROJECT_ID] [--region REGION] [--prefix PREFIX] [--keep-log-bucket | --purge-all] [--include-project-wide]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --keep-log-bucket) LOG_BUCKET_MODE="keep"; shift ;;
    --purge-all) LOG_BUCKET_MODE="purge"; shift ;;
    --include-project-wide) INCLUDE_PROJECT_WIDE="true"; shift ;;
    *) usage ;;
  esac
done

TFVARS="${TF_DIR}/terraform.tfvars"
tfvars_val() {
  local key="$1"
  if [[ -f "${TFVARS}" ]]; then
    sed -n -E "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*\"([^\"]+)\".*/\1/p" "${TFVARS}" | head -n 1
  fi
}

# tf_out NAME prints a Terraform output only when it is a plain value. With an
# empty state, `terraform output` can print a warning on stdout.
tf_out() {
  local v
  v="$(terraform -chdir="${TF_DIR}" output -raw "$1" 2>/dev/null || true)"
  if [[ "${v}" =~ ^[a-z][a-z0-9-]*[a-z0-9]$ ]]; then
    echo "${v}"
  fi
}

if [[ -z "${PROJECT}" ]]; then
  PROJECT="$(tf_out project_id)"
fi
if [[ -z "${PROJECT}" ]]; then
  PROJECT="$(tfvars_val project_id)"
fi

if [[ -z "${REGION}" ]]; then
  REGION="$(tf_out region)"
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

echo "This resets the agent governance starter pack in project ${PROJECT} (${REGION}, prefix=${PREFIX})."
echo "Project-wide steps: $([[ "${INCLUDE_PROJECT_WIDE}" == "true" ]] && echo "ON (--include-project-wide)" || echo "report only")."
read -r -p "Type the project ID to continue: " answer
if [[ "${answer}" != "${PROJECT}" ]]; then
  echo "Stopped. Nothing was deleted."
  exit 1
fi

fail() {
  echo "ERROR: $*" >&2
  FAILURES=$((FAILURES + 1))
}

# 1. Run terraform destroy when state exists
if [[ -f "${TF_DIR}/terraform.tfstate" ]]; then
  STATE_COUNT="$(jq '.resources | length' "${TF_DIR}/terraform.tfstate" 2>/dev/null || echo 0)"
  if [[ "${STATE_COUNT}" -gt 0 ]]; then
    if [[ "${LOG_BUCKET_MODE}" == "keep" ]]; then
      echo "Detaching the audit log bucket from Terraform state before destroy (--keep-log-bucket)..."
      terraform -chdir="${TF_DIR}" state rm google_logging_project_bucket_config.audit 2>/dev/null || true
    fi
    echo "Running terraform destroy..."
    if ! terraform -chdir="${TF_DIR}" destroy -auto-approve; then
      fail "terraform destroy reported an error. The sweep continues. Run this script again after it finishes."
    fi
  fi
fi

# Use the Application Default Credentials token. The gcloud CLI token can be
# bound to Certificate Based Access and then fails on these REST endpoints.
TOKEN="$(gcloud auth application-default print-access-token 2>/dev/null || true)"
if [[ -z "${TOKEN}" ]]; then
  echo "ERROR: Run 'gcloud auth application-default login' first." >&2
  exit 1
fi

# api_get URL -> prints the HTTP status code.
api_get() {
  curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" "$1"
}

# api_delete LABEL URL OPERATION_BASE
# Sends DELETE, then waits up to 10 minutes for the long-running operation.
api_delete() {
  local label="$1" url="$2" op_base="$3" body code op i
  body="$(mktemp)"
  code="$(curl -s -o "${body}" -w "%{http_code}" -X DELETE \
    -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" "${url}")"
  if [[ "${code}" != "200" ]]; then
    fail "Delete of ${label} returned HTTP ${code}: $(jq -r '.error.message // empty' "${body}" 2>/dev/null)"
    rm -f "${body}"
    return 0
  fi
  op="$(jq -r 'if (.name // "") | test("/operations/") then .name else empty end' "${body}" 2>/dev/null || true)"
  rm -f "${body}"
  if [[ -z "${op}" ]]; then
    echo "Deleted ${label}."
    return 0
  fi
  for i in $(seq 1 60); do
    local status
    status="$(curl -s -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" "${op_base}/${op}")"
    if [[ "$(echo "${status}" | jq -r '.done // false')" == "true" ]]; then
      if [[ "$(echo "${status}" | jq -r 'has("error")')" == "true" ]]; then
        fail "Delete of ${label} failed: $(echo "${status}" | jq -r '.error.message')"
      else
        echo "Deleted ${label}."
      fi
      return 0
    fi
    sleep 10
  done
  fail "Delete of ${label} did not finish in 10 minutes (${op})."
}

AIP="https://${REGION}-aiplatform.googleapis.com/v1"
NSEC="https://networksecurity.googleapis.com/v1"
NSVC="https://networkservices.googleapis.com/v1"
LOC="projects/${PROJECT}/locations/${REGION}"

# 2. Out-of-state sweep: Reasoning Engines named <prefix>-reference-agent
echo "Checking for leftover Reasoning Engines (${PREFIX}-reference-agent)..."
RE_LIST="$(curl -s -H "Authorization: Bearer ${TOKEN}" "${AIP}/${LOC}/reasoningEngines" || echo "{}")"
for re_name in $(echo "${RE_LIST}" | jq -r --arg dn "${PREFIX}-reference-agent" '.reasoningEngines[]? | select(.displayName == $dn) | .name'); do
  api_delete "Reasoning Engine ${re_name}" "${AIP}/${re_name}?force=true" "${AIP}"
done

# 3. Out-of-state sweep: authz policies first. A gateway and an authz extension
#    cannot be deleted cleanly while a policy still uses them.
for pol in "${PREFIX}-egress-iap-policy" "${PREFIX}-egress-ma-policy" "${PREFIX}-ingress-ma-policy"; do
  if [[ "$(api_get "${NSEC}/${LOC}/authzPolicies/${pol}")" == "200" ]]; then
    api_delete "authzPolicy ${pol}" "${NSEC}/${LOC}/authzPolicies/${pol}" "${NSEC}"
  fi
done

# 4. Out-of-state sweep: gateways, then authz extensions
for gw in "${PREFIX}-egress" "${PREFIX}-ingress"; do
  if [[ "$(api_get "${NSVC}/${LOC}/agentGateways/${gw}")" == "200" ]]; then
    api_delete "agentGateway ${gw}" "${NSVC}/${LOC}/agentGateways/${gw}" "${NSVC}"
  fi
done
for ext in "${PREFIX}-egress-iap-authz" "${PREFIX}-egress-ma-authz"; do
  if [[ "$(api_get "${NSVC}/${LOC}/authzExtensions/${ext}")" == "200" ]]; then
    api_delete "authzExtension ${ext}" "${NSVC}/${LOC}/authzExtensions/${ext}" "${NSVC}"
  fi
done

# 5. Out-of-state sweep: IAM V2 policy bindings and access policies
IAM2="https://iam.googleapis.com/v2"
for pb in "${PREFIX}-agent-egress" "${PREFIX}-egress-access"; do
  URL="${IAM2}/policies/cloudresourcemanager.googleapis.com%2Fprojects%2F${PROJECT}/policyBindings/${pb}"
  if [[ "$(api_get "${URL}")" == "200" ]]; then
    api_delete "IAM policyBinding ${pb}" "${URL}" "${IAM2}"
  fi
done
IAM2B="https://iam.googleapis.com/v2beta"
for ap in "${PREFIX}-agent-egress" "${PREFIX}-egress-access"; do
  URL="${IAM2B}/projects/${PROJECT}/locations/global/accessPolicies/${ap}"
  if [[ "$(api_get "${URL}")" == "200" ]]; then
    api_delete "IAM accessPolicy ${ap}" "${URL}" "${IAM2B}"
  fi
done

# 6. Out-of-state sweep: Agent Registry entries
AREG="https://agentregistry.googleapis.com/v1alpha"
for svc in "${PREFIX}-work-items" "${PREFIX}-sample-mcp" "${PREFIX}-google-apis" "${PREFIX}-vertex-endpoint"; do
  for collection in "services" "mcpServers" "endpoints"; do
    URL="${AREG}/${LOC}/${collection}/${svc}"
    if [[ "$(api_get "${URL}")" == "200" ]]; then
      api_delete "Agent Registry ${collection}/${svc}" "${URL}" "${AREG}"
    fi
  done
done

# 7. Out-of-state sweep: Model Armor templates
for tmpl in "${PREFIX}-agw-request" "${PREFIX}-agw-response" "${PREFIX}-prompt-baseline" "${PREFIX}-response-baseline"; do
  if gcloud model-armor templates describe "${tmpl}" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Model Armor template ${tmpl}..."
    gcloud model-armor templates delete "${tmpl}" --location="${REGION}" --project="${PROJECT}" --quiet || fail "Delete of Model Armor template ${tmpl} failed."
  fi
done

# 8. Out-of-state sweep: Cloud Run services, Artifact Registry repositories, and service accounts
for cr in "${PREFIX}-work-items" "${PREFIX}-sample-mcp"; do
  if gcloud run services describe "${cr}" --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Cloud Run service ${cr}..."
    gcloud run services delete "${cr}" --region="${REGION}" --project="${PROJECT}" --quiet || fail "Delete of Cloud Run service ${cr} failed."
  fi
done
for repo in "${PREFIX}-mcp" "${PREFIX}"; do
  if gcloud artifacts repositories describe "${repo}" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Artifact Registry repository ${repo}..."
    gcloud artifacts repositories delete "${repo}" --location="${REGION}" --project="${PROJECT}" --quiet || fail "Delete of repository ${repo} failed."
  fi
done
for sa_short in "${PREFIX}-mcp-build" "${PREFIX}-mcp-run" "${PREFIX}-mcp-invoker" "${PREFIX}-sample-mcp-sa"; do
  SA_EMAIL="${sa_short}@${PROJECT}.iam.gserviceaccount.com"
  if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting service account ${SA_EMAIL}..."
    gcloud iam service-accounts delete "${SA_EMAIL}" --project="${PROJECT}" --quiet || fail "Delete of service account ${SA_EMAIL} failed."
  fi
done

# 9 to 11. Project-wide steps. These are not limited to <prefix>-* resources.
project_wide() {
  local description="$1"
  shift
  if [[ "${INCLUDE_PROJECT_WIDE}" == "true" ]]; then
    echo "${description}..."
    "$@" || fail "${description} failed."
  else
    echo "SKIPPED (report only): ${description}. Pass --include-project-wide to remove it."
  fi
}

# 9. Cloud Build source bucket (shared by every Cloud Build job in the project)
BUCKET="gs://${PROJECT}_${REGION}_cloudbuild"
if gcloud storage buckets describe "${BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
  project_wide "Delete the Cloud Build source bucket ${BUCKET}" gcloud storage rm --recursive "${BUCKET}"
fi

# 10. Model Armor role bindings on every service-*@gcp-sa-dep.iam.gserviceaccount.com member
IAM_JSON="$(gcloud projects get-iam-policy "${PROJECT}" --format=json 2>/dev/null || echo "{}")"
for role in "roles/modelarmor.calloutUser" "roles/modelarmor.user" "roles/serviceusage.serviceUsageConsumer"; do
  for member in $(echo "${IAM_JSON}" | jq -r --arg r "${role}" '
    .bindings[]? | select(.role == $r) | .members[]? | select(contains("@gcp-sa-dep.iam.gserviceaccount.com"))
  '); do
    project_wide "Remove ${role} from ${member}" \
      gcloud projects remove-iam-policy-binding "${PROJECT}" --member="${member}" --role="${role}" --condition=None --quiet
  done
done

# 11. Project-level organization policy overrides for domain restriction
for constraint in "iam.allowedPolicyMemberDomains" "iam.managed.allowedPolicyMembers"; do
  if gcloud org-policies describe "${constraint}" --project="${PROJECT}" >/dev/null 2>&1; then
    project_wide "Delete the project-level organization policy override ${constraint}" \
      gcloud org-policies delete "${constraint}" --project="${PROJECT}"
  fi
done

# 12. Audit log sink and 7-day log bucket protection
for sink in "${PREFIX}-agent-audit" "${PREFIX}-audit"; do
  if gcloud logging sinks describe "${sink}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting log sink ${sink}..."
    gcloud logging sinks delete "${sink}" --project="${PROJECT}" --quiet || fail "Delete of log sink ${sink} failed."
  fi
done

for bkt in "${PREFIX}-agent-audit" "${PREFIX}-audit"; do
  BKT_STATE="$(gcloud logging buckets describe "${bkt}" --location="${REGION}" --project="${PROJECT}" --format="value(lifecycleState)" 2>/dev/null || true)"
  if [[ -n "${BKT_STATE}" ]]; then
    if [[ "${LOG_BUCKET_MODE}" == "keep" ]]; then
      if [[ "${BKT_STATE}" == "DELETE_REQUESTED" ]]; then
        echo "Restoring soft-deleted log bucket ${bkt} (--keep-log-bucket avoids the 7-day soft-delete lock)..."
        gcloud logging buckets undelete "${bkt}" --location="${REGION}" --project="${PROJECT}" || fail "Undelete of log bucket ${bkt} failed."
      fi
      if [[ "${bkt}" == "${PREFIX}-agent-audit" ]]; then
        echo "Re-importing ${bkt} into Terraform state so the next terraform apply succeeds without 409 ALREADY_EXISTS..."
        terraform -chdir="${TF_DIR}" import "google_logging_project_bucket_config.audit" "projects/${PROJECT}/locations/${REGION}/buckets/${bkt}" >/dev/null 2>&1 || true
        if [[ -f "${TF_DIR}/terraform.tfstate" ]]; then
          jq --arg p "${PROJECT}" '
            (.resources[] | select(.type == "google_logging_project_bucket_config" and .name == "audit") | .instances[].attributes.project) = $p
          ' "${TF_DIR}/terraform.tfstate" > "${TF_DIR}/terraform.tfstate.tmp" && mv "${TF_DIR}/terraform.tfstate.tmp" "${TF_DIR}/terraform.tfstate"
        fi
      fi
    elif [[ "${LOG_BUCKET_MODE}" == "purge" && "${BKT_STATE}" == "ACTIVE" ]]; then
      echo "Deleting log bucket ${bkt} (--purge-all). It stays soft-deleted for 7 days..."
      gcloud logging buckets delete "${bkt}" --location="${REGION}" --project="${PROJECT}" --quiet || fail "Delete of log bucket ${bkt} failed."
    fi
  fi
done

# 13. Local build artifacts
rm -f "${TF_DIR}/build/agent_source.tar.gz" "${TF_DIR}/build/agent-src.tar.gz" "${TF_DIR}/tfplan"

echo "Remaining resources in Terraform state:"
terraform -chdir="${TF_DIR}" state list 2>/dev/null || true

if [[ "${FAILURES}" -gt 0 ]]; then
  echo "Clean-up NOT complete: ${FAILURES} step(s) failed. Read the errors above, then run this script again." >&2
  exit 1
fi
echo "Clean-up done."
