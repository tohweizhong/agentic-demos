#!/usr/bin/env bash
# Deploy ge-prober as a Google Cloud Run Job with parameterized Cloud Scheduler trigger
set -euo pipefail

# ==============================================================================
# Configuration & Defaults
# ==============================================================================
PROJECT_ID="${GCP_PROJECT_ID:-weizhong-project03}"
REGION="${GCP_REGION:-us-central1}"
ENGINE_ID="${GE_ENGINE_ID:-ge-global-prober_1786960389717}"
LOCATION="${GE_LOCATION:-global}"
JOB_NAME="${JOB_NAME:-ge-prober-daily}"
SCHEDULER_JOB="${SCHEDULER_JOB_NAME:-}"
SCHEDULE_CRON="${SCHEDULE_CRON:-0 1 * * *}"
TIME_ZONE="${TIME_ZONE:-Asia/Singapore}"
SERVICE_ACCOUNT="${SCHEDULER_SA_EMAIL:-}"
DRY_RUN=false
SKIP_BUILD=false
ONLY_SCHEDULER=false

# ==============================================================================
# Help / Usage Function
# ==============================================================================
show_usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deploy ge-prober as a Google Cloud Run Job and configure its Cloud Scheduler trigger.

Options:
  -p, --project PROJECT_ID          Google Cloud Project ID (default: \$GCP_PROJECT_ID or 'weizhong-project03')
  -r, --region REGION               Google Cloud Region (default: \$GCP_REGION or 'us-central1')
  -e, --engine-id ENGINE_ID         Gemini Enterprise Engine ID (default: \$GE_ENGINE_ID)
  -l, --location LOCATION           Gemini Enterprise Engine Location (default: \$GE_LOCATION or 'global')
  -j, --job-name JOB_NAME           Cloud Run Job name (default: 'ge-prober-daily')
  -n, --scheduler-name NAME         Cloud Scheduler Job name (default: 'trigger-<JOB_NAME>')
  -s, --schedule CRON_EXPR          Cron schedule expression (default: \$SCHEDULE_CRON or '0 1 * * *')
  -z, --time-zone TIMEZONE          Time zone for schedule (default: \$TIME_ZONE or 'Asia/Singapore')
  -a, --service-account EMAIL       Service account email for invocation (default: \$SCHEDULER_SA_EMAIL or active gcloud account)
      --dry-run                     Preview planned commands and parameters without making changes
      --skip-build                  Deploy Cloud Run Job using existing image tag without running Cloud Build
      --only-scheduler              Configure or update Cloud Scheduler trigger only (skip container build & job deployment)
  -h, --help                        Display this help message and exit

Environment Variables:
  GCP_PROJECT_ID, GCP_REGION, GE_ENGINE_ID, GE_LOCATION, JOB_NAME,
  SCHEDULER_JOB_NAME, SCHEDULE_CRON, TIME_ZONE, SCHEDULER_SA_EMAIL

Examples:
  # Deploy with default settings (daily at 01:00 UTC / 09:00 SGT)
  ./deploy_job.sh

  # Perform a dry-run check with custom project and schedule
  ./deploy_job.sh --dry-run --project="my-gcp-project" --schedule="0 4 * * *" --time-zone="UTC"

  # Update only Cloud Scheduler schedule and dedicated Service Account
  ./deploy_job.sh --only-scheduler --schedule="*/30 * * * *" --service-account="prober-runner@my-proj.iam.gserviceaccount.com"
EOF
}

# ==============================================================================
# Argument Parsing
# ==============================================================================
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--project)
      PROJECT_ID="$2"
      shift 2
      ;;
    --project=*)
      PROJECT_ID="${1#*=}"
      shift
      ;;
    -r|--region)
      REGION="$2"
      shift 2
      ;;
    --region=*)
      REGION="${1#*=}"
      shift
      ;;
    -e|--engine-id)
      ENGINE_ID="$2"
      shift 2
      ;;
    --engine-id=*)
      ENGINE_ID="${1#*=}"
      shift
      ;;
    -l|--location)
      LOCATION="$2"
      shift 2
      ;;
    --location=*)
      LOCATION="${1#*=}"
      shift
      ;;
    -j|--job-name)
      JOB_NAME="$2"
      shift 2
      ;;
    --job-name=*)
      JOB_NAME="${1#*=}"
      shift
      ;;
    -n|--scheduler-name)
      SCHEDULER_JOB="$2"
      shift 2
      ;;
    --scheduler-name=*)
      SCHEDULER_JOB="${1#*=}"
      shift
      ;;
    -s|--schedule)
      SCHEDULE_CRON="$2"
      shift 2
      ;;
    --schedule=*)
      SCHEDULE_CRON="${1#*=}"
      shift
      ;;
    -z|--time-zone)
      TIME_ZONE="$2"
      shift 2
      ;;
    --time-zone=*)
      TIME_ZONE="${1#*=}"
      shift
      ;;
    -a|--service-account)
      SERVICE_ACCOUNT="$2"
      shift 2
      ;;
    --service-account=*)
      SERVICE_ACCOUNT="${1#*=}"
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --only-scheduler)
      ONLY_SCHEDULER=true
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo "Error: Unknown argument '$1'" >&2
      echo "Run '$0 --help' for usage instructions." >&2
      exit 1
      ;;
  esac
done

# Resolve default scheduler job name if not explicitly set
if [[ -z "${SCHEDULER_JOB}" ]]; then
  SCHEDULER_JOB="trigger-${JOB_NAME}"
fi

# Resolve service account email if not set
if [[ -z "${SERVICE_ACCOUNT}" ]]; then
  if command -v gcloud >/dev/null 2>&1; then
    SERVICE_ACCOUNT="$(gcloud config get-value account 2>/dev/null || echo "")"
  fi
  if [[ -z "${SERVICE_ACCOUNT}" ]]; then
    SERVICE_ACCOUNT="default-service-account"
  fi
fi

IMAGE_TAG="gcr.io/${PROJECT_ID}/${JOB_NAME}:latest"
URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run"

echo "================================================================================"
if [[ "${DRY_RUN}" == true ]]; then
  echo "🔍 [DRY RUN MODE] Resolving ge-prober Deployment & Cloud Scheduler Trigger"
else
  echo "🚀 Deploying ge-prober to Google Cloud Run Job with Cloud Scheduler"
fi
echo "================================================================================"
echo "Project ID         : ${PROJECT_ID}"
echo "Region             : ${REGION}"
echo "Engine ID          : ${ENGINE_ID}"
echo "Location           : ${LOCATION}"
echo "Job Name           : ${JOB_NAME}"
echo "Image Tag          : ${IMAGE_TAG}"
echo "Scheduler Name     : ${SCHEDULER_JOB}"
echo "Schedule Cron      : ${SCHEDULE_CRON}"
echo "Time Zone          : ${TIME_ZONE}"
echo "Service Account    : ${SERVICE_ACCOUNT}"
echo "Execution URI      : ${URI}"
echo "Skip Build         : ${SKIP_BUILD}"
echo "Only Scheduler     : ${ONLY_SCHEDULER}"
echo "================================================================================"

# ==============================================================================
# Dry Run Execution Plan
# ==============================================================================
if [[ "${DRY_RUN}" == true ]]; then
  echo "Planned Operations:"
  if [[ "${ONLY_SCHEDULER}" == false ]]; then
    if [[ "${SKIP_BUILD}" == false ]]; then
      echo "1. [Build] gcloud builds submit --project=\"${PROJECT_ID}\" --tag=\"${IMAGE_TAG}\" ."
    else
      echo "1. [Build] (Skipped via --skip-build)"
    fi
    echo "2. [Run Job] gcloud run jobs deploy \"${JOB_NAME}\" \\"
    echo "     --project=\"${PROJECT_ID}\" \\"
    echo "     --region=\"${REGION}\" \\"
    echo "     --image=\"${IMAGE_TAG}\" \\"
    echo "     --tasks=1 \\"
    echo "     --max-retries=0 \\"
    echo "     --task-timeout=300s \\"
    echo "     --memory=1Gi \\"
    echo "     --cpu=2 \\"
    echo "     --set-env-vars=\"GCP_PROJECT_ID=${PROJECT_ID},GE_ENGINE_ID=${ENGINE_ID},GE_LOCATION=${LOCATION}\""
  else
    echo "1. [Run & Build] (Skipped via --only-scheduler)"
  fi

  echo "3. [Scheduler] Configuring Cloud Scheduler trigger (${SCHEDULER_JOB}):"
  echo "   gcloud scheduler jobs create http \"${SCHEDULER_JOB}\" (or update) \\"
  echo "     --project=\"${PROJECT_ID}\" \\"
  echo "     --location=\"${REGION}\" \\"
  echo "     --schedule=\"${SCHEDULE_CRON}\" \\"
  echo "     --time-zone=\"${TIME_ZONE}\" \\"
  echo "     --uri=\"${URI}\" \\"
  echo "     --http-method=POST \\"
  echo "     --oauth-service-account-email=\"${SERVICE_ACCOUNT}\""
  echo ""
  echo "✅ Dry-run validation passed."
  exit 0
fi

# ==============================================================================
# Step 1: Container Build
# ==============================================================================
if [[ "${ONLY_SCHEDULER}" == false ]]; then
  if [[ "${SKIP_BUILD}" == false ]]; then
    echo "📦 [1/3] Building container via Google Cloud Build..."
    gcloud builds submit --project="${PROJECT_ID}" --tag="${IMAGE_TAG}" .
  else
    echo "⏩ [1/3] Skipping container build (--skip-build specified)."
  fi

  # ==============================================================================
  # Step 2: Deploy Cloud Run Job
  # ==============================================================================
  echo "⚡ [2/3] Deploying Cloud Run Job ${JOB_NAME}..."
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
fi

# ==============================================================================
# Step 3: Configure Cloud Scheduler Trigger
# ==============================================================================
echo "⏰ [3/3] Configuring Cloud Scheduler job ${SCHEDULER_JOB}..."
if gcloud scheduler jobs describe "${SCHEDULER_JOB}" --project="${PROJECT_ID}" --location="${REGION}" >/dev/null 2>&1; then
  echo "Updating existing Cloud Scheduler job ${SCHEDULER_JOB}..."
  gcloud scheduler jobs update http "${SCHEDULER_JOB}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="${SCHEDULE_CRON}" \
    --time-zone="${TIME_ZONE}" \
    --uri="${URI}" \
    --http-method=POST \
    --oauth-service-account-email="${SERVICE_ACCOUNT}"
else
  echo "Creating new Cloud Scheduler job ${SCHEDULER_JOB}..."
  gcloud scheduler jobs create http "${SCHEDULER_JOB}" \
    --project="${PROJECT_ID}" \
    --location="${REGION}" \
    --schedule="${SCHEDULE_CRON}" \
    --time-zone="${TIME_ZONE}" \
    --uri="${URI}" \
    --http-method=POST \
    --oauth-service-account-email="${SERVICE_ACCOUNT}"
fi

echo "================================================================================"
echo "✅ Deployment complete! To execute manually:"
echo "   gcloud run jobs execute ${JOB_NAME} --project=${PROJECT_ID} --region=${REGION}"
echo "================================================================================"
