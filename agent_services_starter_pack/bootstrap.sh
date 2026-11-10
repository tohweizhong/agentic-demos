#!/usr/bin/env bash
# Prepares a project for the agent services starter pack. Safe to run again.
#
# 1. Turns on the APIs.
# 2. Sets the observability default storage location to REGION, so that the
#    system creates the _Trace bucket in REGION. Run this before the first trace.
# 3. Creates the staging bucket for the deploy files.
#
# Usage: ./bootstrap.sh   (reads PROJECT_ID, REGION, STAGING_BUCKET from .env)
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing. Copy .env.example to .env and set the values." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
: "${PROJECT_ID:?Set PROJECT_ID in .env}"
: "${STAGING_BUCKET:?Set STAGING_BUCKET in .env}"
REGION="${REGION:-asia-southeast1}"

echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"

echo
echo "== 1. Turn on the APIs"
gcloud services enable --project="${PROJECT_ID}" \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  telemetry.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudtrace.googleapis.com \
  observability.googleapis.com

echo
echo "== 2. Set the observability default storage location to ${REGION}"
EXISTING="$(gcloud observability buckets list --project="${PROJECT_ID}" \
  --location=global --format='value(name)' 2>/dev/null || true)"
if [[ -n "${EXISTING}" ]]; then
  echo "WARNING: observability buckets already exist in location global:"
  echo "${EXISTING}"
  echo "The setting does not move them. See the reprovision procedure in the README."
fi
gcloud observability settings update --project="${PROJECT_ID}" \
  --location=global \
  --update-mask=default_storage_location \
  --default-storage-location="${REGION}" \
  --quiet
gcloud observability settings describe --project="${PROJECT_ID}" \
  --location=global --format='value(defaultStorageLocation)'

echo
echo "== 3. Create the staging bucket gs://${STAGING_BUCKET}"
if gcloud storage buckets describe "gs://${STAGING_BUCKET}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "The bucket exists. No change."
else
  gcloud storage buckets create "gs://${STAGING_BUCKET}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --uniform-bucket-level-access
fi

echo
echo "BOOTSTRAP: DONE. Next: python deploy.py"
