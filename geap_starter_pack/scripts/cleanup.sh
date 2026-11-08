#!/usr/bin/env bash
# Deletes the mini build resources and nothing else.
#
# 1. `terraform destroy` deletes everything in the Terraform state.
# 2. The script deletes the regional Cloud Build source bucket that
#    `gcloud builds submit` made for the MCP image, if it exists.
#
# The APIs stay on. The log bucket stays in a soft-deleted state for 7 days, so
# the same bucket ID cannot be used again in that time.
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need terraform gcloud

PROJECT="$(tf_output project_id)"
REGION="$(tf_output region)"

echo "This deletes the GEAP mini build in project ${PROJECT}."
read -r -p "Type the project ID to continue: " answer
if [[ "${answer}" != "${PROJECT}" ]]; then
  echo "Stopped. Nothing was deleted."
  exit 1
fi

terraform -chdir="${TF_DIR}" destroy

BUCKET="gs://${PROJECT}_${REGION}_cloudbuild"
if gcloud storage buckets describe "${BUCKET}" --project="${PROJECT}" >/dev/null 2>&1; then
  echo "Deleting the Cloud Build source bucket ${BUCKET}."
  gcloud storage rm --recursive "${BUCKET}"
else
  echo "No Cloud Build source bucket ${BUCKET}. Nothing to delete."
fi

echo "Clean-up done. Check that the state is empty:"
terraform -chdir="${TF_DIR}" state list || true
