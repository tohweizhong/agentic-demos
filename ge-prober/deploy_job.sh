#!/usr/bin/env bash
# Deploy ge-prober as a Google Cloud Run Job with daily Cloud Scheduler trigger
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-weizhong-project03}"
REGION="${GCP_REGION:-us-central1}"
ENGINE_ID="${GE_ENGINE_ID:-ge-global-prober_1786960389717}"
LOCATION="${GE_LOCATION:-global}"
JOB_NAME="ge-prober-daily"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${JOB_NAME}:latest"

echo "================================================================================"
echo "🚀 Deploying ge-prober to Google Cloud Run Job"
echo "================================================================================"
echo "Project ID  : ${PROJECT_ID}"
echo "Region      : ${REGION}"
echo "Engine ID   : ${ENGINE_ID}"
echo "Location    : ${LOCATION}"
echo "Job Name    : ${JOB_NAME}"
echo "Image Tag   : ${IMAGE_TAG}"
echo "================================================================================"

# 1. Build and push container using Google Cloud Build
echo "📦 Building container via Google Cloud Build..."
gcloud builds submit --project="${PROJECT_ID}" --tag="${IMAGE_TAG}" .

# 2. Deploy or update Cloud Run Job with environment variables
echo "⚡ Deploying Cloud Run Job ${JOB_NAME}..."
gcloud run jobs deploy "${JOB_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_TAG}" \
  --tasks=1 \
  --max-retries=0 \
  --task-timeout=300s \
  --memory=1Gi \
  --cpu=2 \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GE_ENGINE_ID=${ENGINE_ID},GE_LOCATION=${LOCATION}"

# 3. Setup / Update Cloud Scheduler trigger (Daily at 01:00 UTC / 09:00 SGT)
SCHEDULER_JOB="trigger-${JOB_NAME}"
echo "⏰ Configuring Cloud Scheduler job ${SCHEDULER_JOB}..."
if gcloud scheduler jobs describe "${SCHEDULER_JOB}" --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud scheduler jobs update http "${SCHEDULER_JOB}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="0 1 * * *" \
    --time-zone="Asia/Singapore" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="$(gcloud config get-value account)"
else
  gcloud scheduler jobs create http "${SCHEDULER_JOB}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="0 1 * * *" \
    --time-zone="Asia/Singapore" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="$(gcloud config get-value account)"
fi

echo "================================================================================"
echo "✅ Deployment complete! To execute manually:"
echo "   gcloud run jobs execute ${JOB_NAME} --project=${PROJECT_ID} --region=${REGION}"
echo "================================================================================"
