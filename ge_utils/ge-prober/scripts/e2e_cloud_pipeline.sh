#!/usr/bin/env bash
# ==============================================================================
# e2e_cloud_pipeline.sh
# End-to-End Cloud Verification Pipeline for Gemini Enterprise Prober (ge-prober)
#
# Builds container via Cloud Build -> Deploys Cloud Run Job & Cloud Scheduler ->
# Triggers live job execution -> Captures execution logs to local audit artifacts.
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/.."
cd "${ROOT_DIR}"

# --- Default Parameters ---
PROJECT_ID=""
REGION=""
JOB_NAME="ge-prober-daily"
ENGINE_ID=""
DATA_STORE_IDS=""
TRACK_ID=""
SKIP_BUILD=false
DRY_RUN=false
ALERT_EMAIL=""
ALERT_MODE="disabled"

# --- Usage / Help ---
show_help() {
  cat <<'HELP_EOF'
Usage: ./scripts/e2e_cloud_pipeline.sh [OPTIONS]

Executes the full End-to-End Cloud Run pipeline and captures execution logs locally.

Options:
  --project=PROJECT_ID        Target Google Cloud Project ID (default: config.json or gcloud default)
  --region=REGION             Target Google Cloud Region (default: asia-southeast1)
  --job-name=JOB_NAME         Cloud Run Job name (default: ge-prober-daily)
  --engine-id=ENGINE_ID       Target Discovery Engine App / Engine ID
  --datastores=DATA_STORE_IDS Comma-separated list of Data Store IDs
  --track-id=TRACK_ID         Conductor track ID to attach audit execution.log artifact
  --alert-email=EMAIL         Email address for Cloud Monitoring alerts
  --skip-build                Skip Cloud Build container compilation (reuse existing image)
  --dry-run                   Print execution steps and commands without running them
  -h, --help                  Display this help message and exit

Examples:
  ./scripts/e2e_cloud_pipeline.sh
  ./scripts/e2e_cloud_pipeline.sh --track-id=automated_cloud_e2e_pipeline_and_log_artifacts_20260819
  ./scripts/e2e_cloud_pipeline.sh --dry-run
HELP_EOF
}

# --- Parse Arguments ---
for arg in "$@"; do
  case "${arg}" in
    --project=*)
      PROJECT_ID="${arg#*=}"
      ;;
    --region=*)
      REGION="${arg#*=}"
      ;;
    --job-name=*)
      JOB_NAME="${arg#*=}"
      ;;
    --engine-id=*)
      ENGINE_ID="${arg#*=}"
      ;;
    --datastores=*)
      DATA_STORE_IDS="${arg#*=}"
      ;;
    --track-id=*)
      TRACK_ID="${arg#*=}"
      ;;
    --alert-email=*)
      ALERT_EMAIL="${arg#*=}"
      ALERT_MODE="create_or_update"
      ;;
    --skip-build)
      SKIP_BUILD=true
      ;;
    --dry-run)
      DRY_RUN=true
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "❌ Error: Unknown argument '${arg}'" >&2
      show_help >&2
      exit 1
      ;;
  esac
done

# --- Resolve Defaults from config.json or gcloud ---
if [ -z "${PROJECT_ID}" ]; then
  if [ -f "config.json" ]; then
    PROJECT_ID=$(grep -o '"project_id": *"[^"]*"' config.json | head -n1 | cut -d'"' -f4 || true)
  fi
  if [ -z "${PROJECT_ID}" ]; then
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
  fi
fi

if [ -z "${REGION}" ]; then
  if [ -f "config.json" ]; then
    REGION=$(grep -o '"location": *"[^"]*"' config.json | head -n1 | cut -d'"' -f4 || true)
  fi
  if [ -z "${REGION}" ] || [ "${REGION}" = "global" ]; then
    REGION="asia-southeast1"
  fi
fi

if [ -z "${ENGINE_ID}" ] && [ -f "config.json" ]; then
  ENGINE_ID=$(grep -o '"engine_id": *"[^"]*"' config.json | head -n1 | cut -d'"' -f4 || true)
fi

# Auto-detect active track ID if not explicitly specified
if [ -z "${TRACK_ID}" ] && [ -f "conductor/tracks.md" ]; then
  TRACK_ID=$(grep -o 'tracks/[^/)]*' conductor/tracks.md | tail -n1 | sed 's|tracks/||' || true)
fi

if [ -z "${GCP_ACCESS_TOKEN:-}" ]; then
  GCP_ACCESS_TOKEN=$(gcloud auth application-default print-access-token 2>/dev/null || gcloud auth print-access-token 2>/dev/null || true)
  if [ -n "${GCP_ACCESS_TOKEN}" ]; then
    export GCP_ACCESS_TOKEN
  fi
fi

TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
EXEC_LOG_DIR="${ROOT_DIR}/logs/executions"
mkdir -p "${EXEC_LOG_DIR}"

TRACK_LOG_PATH=""
if [ -n "${TRACK_ID}" ]; then
  TRACK_LOG_PATH="conductor/tracks/${TRACK_ID}/execution.log"
fi

echo "================================================================================"
echo "🚀 END-TO-END CLOUD VERIFICATION PIPELINE (ge-prober)"
echo "================================================================================"
echo "🎯 Project ID    : ${PROJECT_ID}"
echo "📍 Region        : ${REGION}"
echo "⚙️ Job Name      : ${JOB_NAME}"
echo "🏷️ Active Track  : ${TRACK_ID:-None}"
echo "📁 Track Log     : ${TRACK_LOG_PATH:-None}"
echo "📁 Logs Dir      : logs/executions/"
echo "⚡ Skip Build    : ${SKIP_BUILD}"
echo "🔍 Dry Run       : ${DRY_RUN}"
echo "================================================================================"
echo

if [ "${DRY_RUN}" = "true" ]; then
  echo "👉 [DRY RUN] Step 1: Deploy Cloud Run Job & Cloud Scheduler"
  echo "   Command: bash deploy_job.sh --project=${PROJECT_ID} --region=${REGION} --job-name=${JOB_NAME} --engine-id=${ENGINE_ID}"
  echo
  echo "👉 [DRY RUN] Step 2: Trigger Live Cloud Run Job Execution"
  echo "   Command: gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID} --wait --format=json"
  echo
  echo "👉 [DRY RUN] Step 3: Extract and format execution task logs"
  echo "   Destinations:"
  echo "     - ${EXEC_LOG_DIR}/${TIMESTAMP}_${JOB_NAME}-dryrun.log"
  if [ -n "${TRACK_LOG_PATH}" ]; then
    echo "     - ${TRACK_LOG_PATH}"
  fi
  echo
  echo "✅ [DRY RUN] Pipeline simulation completed successfully."
  exit 0
fi

# --- Step 1: Deploy Job via deploy_job.sh ---
echo "▶️ [Step 1/3] Deploying Cloud Run Job and updating Cloud Scheduler..."
DEPLOY_CMD="bash deploy_job.sh --project=${PROJECT_ID} --region=${REGION} --job-name=${JOB_NAME}"
if [ -n "${ENGINE_ID}" ]; then
  DEPLOY_CMD="${DEPLOY_CMD} --engine-id=${ENGINE_ID}"
fi
if [ -n "${DATA_STORE_IDS}" ]; then
  DEPLOY_CMD="${DEPLOY_CMD} --datastores=${DATA_STORE_IDS}"
fi
if [ "${SKIP_BUILD}" = "true" ]; then
  DEPLOY_CMD="${DEPLOY_CMD} --skip-build"
fi
if [ -n "${ALERT_EMAIL}" ]; then
  DEPLOY_CMD="${DEPLOY_CMD} --alert-email=${ALERT_EMAIL}"
fi

eval "${DEPLOY_CMD}"

# --- Step 2: Trigger Execution ---
echo
echo "▶️ [Step 2/3] Triggering Cloud Run Job execution (${JOB_NAME})..."
EXECUTION_OUTPUT=$(gcloud run jobs execute "${JOB_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --wait --format="value(metadata.name)")
EXECUTION_NAME="${EXECUTION_OUTPUT##*/}"
echo "✅ Cloud Run Execution Completed: ${EXECUTION_NAME}"

# --- Step 3: Extract Logs ---
echo
echo "▶️ [Step 3/3] Fetching execution logs from Google Cloud Logging..."
LOCAL_LOG_FILE="${EXEC_LOG_DIR}/${TIMESTAMP}_${EXECUTION_NAME}.log"

# Fetch logs directly using gcloud beta or cloud logging read
set +e
LOGS=$(gcloud logging read "resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"${JOB_NAME}\" AND labels.\"run.googleapis.com/execution_name\"=\"${EXECUTION_NAME}\"" \
  --project="${PROJECT_ID}" \
  --format="value(textPayload)" \
  --order="asc" \
  --limit=500 2>/dev/null)
set -e

if [ -z "${LOGS}" ]; then
  # Fallback to standard beta execution logs if logging read returned empty
  set +e
  LOGS=$(gcloud beta run jobs executions logs "${EXECUTION_NAME}" --region="${REGION}" --project="${PROJECT_ID}" 2>/dev/null)
  set -e
fi

# Write local execution log
echo "${LOGS}" > "${LOCAL_LOG_FILE}"
echo "📝 Execution log written to: ${LOCAL_LOG_FILE}"

# Write track artifact if track directory exists
if [ -n "${TRACK_LOG_PATH}" ]; then
  mkdir -p "$(dirname "${TRACK_LOG_PATH}")"
  echo "${LOGS}" > "${TRACK_LOG_PATH}"
  echo "📝 Track audit log artifact written to: ${TRACK_LOG_PATH}"
fi

echo
echo "================================================================================"
echo "📊 PIPELINE EXECUTION VERIFICATION"
echo "================================================================================"
if echo "${LOGS}" | grep -q "TEST SUITE EXECUTION SUMMARY"; then
  echo "✅ Verified: Prober executed to completion and generated Execution Summary."
else
  echo "⚠️ Warning: Could not find 'TEST SUITE EXECUTION SUMMARY' in captured logs."
fi

if echo "${LOGS}" | grep -q "Functional Pass Rate : [0-9]*/[0-9]* (100.0%)"; then
  echo "✅ Verified: 100% Functional Pass Rate achieved."
fi

echo "================================================================================"
echo "🎉 Cloud E2E Pipeline Completed Successfully!"
echo "================================================================================"
