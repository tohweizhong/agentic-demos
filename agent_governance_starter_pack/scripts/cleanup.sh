#!/usr/bin/env bash
# Resets an agent governance starter pack sandbox project cleanly.
#
# 1. Reads PROJECT, REGION, and PREFIX from Terraform outputs or terraform.tfvars.
# 2. Runs `terraform destroy` when Terraform state contains resources.
# 3. Protects against the 7-day Cloud Logging bucket soft-delete lock by
#    undeleting the audit bucket by default (--keep-log-bucket), or deletes it
#    when --purge-all is passed.
# 4. Sweeps any out-of-state GEAP resources, IAM bindings on gcp-sa-dep,
#    project-level org policy overrides, Cloud Build source bucket, and local
#    build artifacts.
#
# Usage:
#   scripts/cleanup.sh [--project PROJECT_ID] [--region REGION] [--prefix PREFIX] [--keep-log-bucket | --purge-all]
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need terraform gcloud jq curl

PROJECT=""
REGION=""
PREFIX=""
LOG_BUCKET_MODE="keep"

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
    --keep-log-bucket)
      LOG_BUCKET_MODE="keep"
      shift
      ;;
    --purge-all)
      LOG_BUCKET_MODE="purge"
      shift
      ;;
    *)
      echo "Usage: $0 [--project PROJECT_ID] [--region REGION] [--prefix PREFIX] [--keep-log-bucket | --purge-all]" >&2
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

echo "This resets the agent governance starter pack in project ${PROJECT} (${REGION}, prefix=${PREFIX})."
read -r -p "Type the project ID to continue: " answer
if [[ "${answer}" != "${PROJECT}" ]]; then
  echo "Stopped. Nothing was deleted."
  exit 1
fi

# 1. Run terraform destroy when state exists
if [[ -f "${TF_DIR}/terraform.tfstate" ]]; then
  STATE_COUNT="$(jq '.resources | length' "${TF_DIR}/terraform.tfstate" 2>/dev/null || echo 0)"
  if [[ "${STATE_COUNT}" -gt 0 ]]; then
    if [[ "${LOG_BUCKET_MODE}" == "keep" ]]; then
      echo "Detaching the audit log bucket from Terraform state before destroy (--keep-log-bucket)..."
      terraform -chdir="${TF_DIR}" state rm google_logging_project_bucket_config.audit 2>/dev/null || true
    fi
    echo "Running terraform destroy..."
    terraform -chdir="${TF_DIR}" destroy -auto-approve || echo "WARN: terraform destroy reported an error. Continuing with out-of-state sweep."
  fi
fi

TOKEN="$(gcloud auth print-access-token)"

# 2. Out-of-state sweep: Reasoning Engines matching <prefix>-reference-agent
echo "Checking for leftover Reasoning Engines (${PREFIX}-reference-agent)..."
RE_LIST="$(curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/reasoningEngines" || echo "{}")"
for re_name in $(echo "${RE_LIST}" | jq -r --arg dn "${PREFIX}-reference-agent" '.reasoningEngines[]? | select(.displayName == $dn) | .name'); do
  echo "Deleting Reasoning Engine ${re_name}..."
  curl -s -X DELETE -H "Authorization: Bearer ${TOKEN}" \
    "https://${REGION}-aiplatform.googleapis.com/v1/${re_name}?force=true" >/dev/null || true
done

# 3. Out-of-state sweep: Network Security authzPolicies
for pol in "${PREFIX}-egress-iap-policy" "${PREFIX}-egress-ma-policy" "${PREFIX}-ingress-ma-policy"; do
  HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
    "https://networksecurity.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzPolicies/${pol}")"
  if [[ "${HTTP_CODE}" == "200" ]]; then
    echo "Deleting authzPolicy ${pol}..."
    curl -s -X DELETE -H "Authorization: Bearer ${TOKEN}" \
      "https://networksecurity.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzPolicies/${pol}" >/dev/null || true
    sleep 15
  fi
done

# 4. Out-of-state sweep: Network Services agentGateways and authzExtensions
for gw in "${PREFIX}-egress" "${PREFIX}-ingress"; do
  HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
    "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/agentGateways/${gw}")"
  if [[ "${HTTP_CODE}" == "200" ]]; then
    echo "Deleting agentGateway ${gw}..."
    curl -s -X DELETE -H "Authorization: Bearer ${TOKEN}" \
      "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/agentGateways/${gw}" >/dev/null || true
  fi
done

for ext in "${PREFIX}-egress-iap-authz" "${PREFIX}-egress-ma-authz"; do
  HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
    "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzExtensions/${ext}")"
  if [[ "${HTTP_CODE}" == "200" ]]; then
    echo "Deleting authzExtension ${ext}..."
    curl -s -X DELETE -H "Authorization: Bearer ${TOKEN}" \
      "https://networkservices.googleapis.com/v1/projects/${PROJECT}/locations/${REGION}/authzExtensions/${ext}" >/dev/null || true
  fi
done

# 5. Out-of-state sweep: IAM V2 policy bindings and access policies
for pb in "${PREFIX}-agent-egress" "${PREFIX}-egress-access"; do
  HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
    "https://iam.googleapis.com/v2/policies/cloudresourcemanager.googleapis.com%2Fprojects%2F${PROJECT}/policyBindings/${pb}")"
  if [[ "${HTTP_CODE}" == "200" ]]; then
    echo "Deleting IAM policyBinding ${pb}..."
    curl -s -X DELETE -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
      "https://iam.googleapis.com/v2/policies/cloudresourcemanager.googleapis.com%2Fprojects%2F${PROJECT}/policyBindings/${pb}" >/dev/null || true
  fi
done

for ap in "${PREFIX}-agent-egress" "${PREFIX}-egress-access"; do
  HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
    "https://iam.googleapis.com/v2beta/projects/${PROJECT}/locations/global/accessPolicies/${ap}")"
  if [[ "${HTTP_CODE}" == "200" ]]; then
    echo "Deleting IAM accessPolicy ${ap}..."
    curl -s -X DELETE -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
      "https://iam.googleapis.com/v2beta/projects/${PROJECT}/locations/global/accessPolicies/${ap}" >/dev/null || true
  fi
done

# 6. Out-of-state sweep: Agent Registry mcpServers and endpoints
for svc in "${PREFIX}-work-items" "${PREFIX}-sample-mcp" "${PREFIX}-google-apis" "${PREFIX}-vertex-endpoint"; do
  for collection in "services" "mcpServers" "endpoints"; do
    HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
      "https://agentregistry.googleapis.com/v1alpha/projects/${PROJECT}/locations/${REGION}/${collection}/${svc}")"
    if [[ "${HTTP_CODE}" == "200" ]]; then
      echo "Deleting Agent Registry ${collection}/${svc}..."
      curl -s -X DELETE -H "Authorization: Bearer ${TOKEN}" -H "x-goog-user-project: ${PROJECT}" \
        "https://agentregistry.googleapis.com/v1alpha/projects/${PROJECT}/locations/${REGION}/${collection}/${svc}" >/dev/null || true
    fi
  done
done

# 7. Out-of-state sweep: Model Armor templates
for tmpl in "${PREFIX}-agw-request" "${PREFIX}-agw-response" "${PREFIX}-prompt-baseline" "${PREFIX}-response-baseline"; do
  if gcloud model-armor templates describe "${tmpl}" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Model Armor template ${tmpl}..."
    gcloud model-armor templates delete "${tmpl}" --location="${REGION}" --project="${PROJECT}" --quiet || true
  fi
done

# 8. Out-of-state sweep: Cloud Run services, Artifact Registry repositories, and service accounts
for cr in "${PREFIX}-work-items" "${PREFIX}-sample-mcp"; do
  if gcloud run services describe "${cr}" --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Cloud Run service ${cr}..."
    gcloud run services delete "${cr}" --region="${REGION}" --project="${PROJECT}" --quiet || true
  fi
done

for repo in "${PREFIX}-mcp" "${PREFIX}"; do
  if gcloud artifacts repositories describe "${repo}" --location="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting Artifact Registry repository ${repo}..."
    gcloud artifacts repositories delete "${repo}" --location="${REGION}" --project="${PROJECT}" --quiet || true
  fi
done

for sa_short in "${PREFIX}-mcp-build" "${PREFIX}-mcp-run" "${PREFIX}-mcp-invoker" "${PREFIX}-sample-mcp-sa"; do
  SA_EMAIL="${sa_short}@${PROJECT}.iam.gserviceaccount.com"
  if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting service account ${SA_EMAIL}..."
    gcloud iam service-accounts delete "${SA_EMAIL}" --project="${PROJECT}" --quiet || true
  fi
done

# 9. Cloud Build source bucket
BUCKET="gs://${PROJECT}_${REGION}_cloudbuild"
if gcloud storage buckets describe "${BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
  echo "Deleting the Cloud Build source bucket ${BUCKET}..."
  gcloud storage rm --recursive "${BUCKET}" || true
fi

# 10. Leftover project-level IAM bindings on service-*@gcp-sa-dep.iam.gserviceaccount.com
IAM_JSON="$(gcloud projects get-iam-policy "${PROJECT}" --format=json 2>/dev/null || echo "{}")"
for role in "roles/modelarmor.calloutUser" "roles/modelarmor.user" "roles/serviceusage.serviceUsageConsumer"; do
  for member in $(echo "${IAM_JSON}" | jq -r --arg r "${role}" '
    .bindings[]? | select(.role == $r) | .members[]? | select(contains("@gcp-sa-dep.iam.gserviceaccount.com"))
  '); do
    echo "Removing ${role} from ${member}..."
    gcloud projects remove-iam-policy-binding "${PROJECT}" --member="${member}" --role="${role}" --condition=None --quiet >/dev/null || true
  done
done

# 11. Leftover project-level organization policy overrides
for constraint in "iam.allowedPolicyMemberDomains" "iam.managed.allowedPolicyMembers"; do
  if gcloud org-policies describe "${constraint}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting project-level organization policy override ${constraint}..."
    gcloud org-policies delete "${constraint}" --project="${PROJECT}" >/dev/null || true
  fi
done

# 12. Audit log sink and 7-day log bucket protection
for sink in "${PREFIX}-agent-audit" "${PREFIX}-audit"; do
  if gcloud logging sinks describe "${sink}" --project="${PROJECT}" >/dev/null 2>&1; then
    echo "Deleting log sink ${sink}..."
    gcloud logging sinks delete "${sink}" --project="${PROJECT}" --quiet || true
  fi
done

for bkt in "${PREFIX}-agent-audit" "${PREFIX}-audit"; do
  BKT_STATE="$(gcloud logging buckets describe "${bkt}" --location="${REGION}" --project="${PROJECT}" --format="value(lifecycleState)" 2>/dev/null || true)"
  if [[ -n "${BKT_STATE}" ]]; then
    if [[ "${LOG_BUCKET_MODE}" == "keep" ]]; then
      if [[ "${BKT_STATE}" == "DELETE_REQUESTED" ]]; then
        echo "Restoring soft-deleted log bucket ${bkt} (--keep-log-bucket avoids the 7-day soft-delete lock)..."
        gcloud logging buckets undelete "${bkt}" --location="${REGION}" --project="${PROJECT}" || true
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
      echo "Deleting log bucket ${bkt} (--purge-all)..."
      gcloud logging buckets delete "${bkt}" --location="${REGION}" --project="${PROJECT}" --quiet || true
    fi
  fi
done

# 13. Local build artifacts
rm -f "${TF_DIR}/build/agent-src.tar.gz" "${TF_DIR}/tfplan"

echo "Clean-up done. Remaining resources in Terraform state:"
terraform -chdir="${TF_DIR}" state list 2>/dev/null || true
