#!/usr/bin/env bash
# Read-only. Recommends the log bucket flag for scripts/cleanup.sh from the facts
# and from what the user plans next. geap-teardown runs it and shows the result.
#
#   scripts/teardown_plan.sh --intent redeploy|done|production [--project P --region R --prefix X]
#
#   redeploy   = deploy again later from this same clone
#   done       = sandbox or rehearsal, this clone will be deleted or not used again
#   production = customer project, audit logs are evidence
# Prints one line:  TEARDOWN_PLAN: <command> | reason: <reason>
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud jq

TFVARS="${TF_DIR}/terraform.tfvars"
val() { [[ -f "${TFVARS}" ]] || return 0; sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*\"\{0,1\}\([^\"#]*\)\"\{0,1\}.*/\1/p" "${TFVARS}" | head -1 | sed 's/[[:space:]]*$//' || true; }

INTENT=""; PROJECT=""; REGION=""; PREFIX=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --intent) INTENT="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    *) echo "ERROR: unknown argument $1" >&2; exit 2 ;;
  esac
done
PROJECT="${PROJECT:-$(val project_id)}"; REGION="${REGION:-$(val region)}"; PREFIX="${PREFIX:-$(val name_prefix)}"; PREFIX="${PREFIX:-geap}"
[[ -n "${PROJECT}" && -n "${REGION}" ]] || { echo "ERROR: no project or region. Pass --project and --region, or set terraform.tfvars." >&2; exit 2; }
[[ "${INTENT}" =~ ^(redeploy|done|production)$ ]] || { echo "ERROR: --intent must be redeploy, done, or production." >&2; exit 2; }

STATE_COUNT=0
if [[ -f "${TF_DIR}/terraform.tfstate" ]]; then
  STATE_COUNT="$(jq '.resources | length' "${TF_DIR}/terraform.tfstate" 2>/dev/null || echo 0)"
fi
BUCKET="${PREFIX}-agent-audit"
if ! gcloud auth print-access-token >/dev/null 2>&1; then
  echo "TEARDOWN_PLAN: ERROR | reason: gcloud has no active account. Run gcloud auth login first."; exit 1
fi
BSTATE="$(gcloud logging buckets describe "${BUCKET}" --location="${REGION}" --project="${PROJECT}" --format='value(lifecycleState)' 2>/dev/null || true)"
BSTATE="${BSTATE:-NOT_FOUND}"

BASE="scripts/cleanup.sh --project ${PROJECT} --region ${REGION} --prefix ${PREFIX}"
if [[ "${BSTATE}" == "DELETE_REQUESTED" ]]; then
  FLAG="--purge-all"; WHY="the bucket ${BUCKET} is already soft-deleted. --keep-log-bucket would restore it"
elif [[ "${INTENT}" == "production" ]]; then
  FLAG="--keep-log-bucket"; WHY="production: audit logs are evidence. Delete them only under the customer retention rules"
elif [[ "${INTENT}" == "redeploy" && "${STATE_COUNT}" -gt 0 ]]; then
  FLAG="--keep-log-bucket"; WHY="redeploy from this clone: the script imports the bucket into this state again"
elif [[ "${INTENT}" == "redeploy" ]]; then
  FLAG="--keep-log-bucket"; WHY="redeploy: keep the bucket. Note: this clone has no state, so the next apply must import the bucket (preflight shows the command)"
else
  FLAG="--purge-all"; WHY="sandbox, clone not used again: a kept bucket would be managed by no Terraform state. A new prefix avoids the 7-day soft delete"
fi
echo "TEARDOWN_PLAN: ${BASE} ${FLAG} | facts: state_resources=${STATE_COUNT} bucket=${BUCKET} bucket_state=${BSTATE} intent=${INTENT} | reason: ${WHY}"
