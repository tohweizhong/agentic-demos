#!/usr/bin/env bash
# Moves the Terraform state to a versioned Cloud Storage bucket (backlog item 20).
# A local state on a laptop or in Cloud Shell is lost when the machine goes away,
# and only one person can use it.
#
#   scripts/init_remote_state.sh            # shows the plan only (default)
#   scripts/init_remote_state.sh --apply    # creates the bucket, writes backend.tf, migrates
#
# Bucket: gs://<project_id>-<name_prefix>-tfstate, in the region of the starter
# pack, with uniform access, public access prevention, and object versioning.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need gcloud terraform

TFVARS="${TF_DIR}/terraform.tfvars"
val() { [[ -f "${TFVARS}" ]] || return 0; sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*\"\{0,1\}\([^\"#]*\)\"\{0,1\}.*/\1/p" "${TFVARS}" | head -1 | sed 's/[[:space:]]*$//' || true; }
APPLY="false"; [[ "${1:-}" == "--apply" ]] && APPLY="true"

PROJECT="$(val project_id)"; REGION="$(val region)"; PREFIX="$(val name_prefix)"; PREFIX="${PREFIX:-geap}"
[[ -n "${PROJECT}" && -n "${REGION}" ]] || { echo "ERROR: set project_id and region in terraform/terraform.tfvars first (scripts/configure.sh)." >&2; exit 2; }
BUCKET="${PROJECT}-${PREFIX}-tfstate"
BACKEND="${TF_DIR}/backend.tf"

echo "REMOTE_STATE plan:"
echo "  1. gcloud storage buckets create gs://${BUCKET} --project=${PROJECT} --location=${REGION} --uniform-bucket-level-access --public-access-prevention"
echo "  2. gcloud storage buckets update gs://${BUCKET} --versioning"
echo "  3. write ${BACKEND##*/}: backend \"gcs\" { bucket = \"${BUCKET}\", prefix = \"agent-governance-starter-pack\" }"
echo "  4. terraform -chdir=terraform init -migrate-state -force-copy"
if [[ "${APPLY}" != "true" ]]; then echo "Plan only. Run again with --apply after review."; exit 0; fi

if [[ -f "${BACKEND}" ]]; then echo "ERROR: ${BACKEND} already exists. Nothing changed." >&2; exit 1; fi
if gcloud storage buckets describe "gs://${BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
  echo "Bucket gs://${BUCKET} already exists. It is used as it is."
else
  gcloud storage buckets create "gs://${BUCKET}" --project="${PROJECT}" --location="${REGION}" --uniform-bucket-level-access --public-access-prevention
fi
gcloud storage buckets update "gs://${BUCKET}" --versioning
cat > "${BACKEND}" <<EOF2
# Written by scripts/init_remote_state.sh. Commit this file only in a private
# customer repository: it names the project.
terraform {
  backend "gcs" {
    bucket = "${BUCKET}"
    prefix = "agent-governance-starter-pack"
  }
}
EOF2
terraform -chdir="${TF_DIR}" init -migrate-state -force-copy -input=false
echo "REMOTE_STATE: done (gs://${BUCKET}/agent-governance-starter-pack). Keep the local terraform.tfstate backup until terraform plan shows no changes."
