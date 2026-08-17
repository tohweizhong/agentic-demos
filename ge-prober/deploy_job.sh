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
SCHEDULE_CRON="${SCHEDULE_CRON:-0 9,17 * * *}"
TIME_ZONE="${TIME_ZONE:-Asia/Singapore}"
SERVICE_ACCOUNT="${SCHEDULER_SA_EMAIL:-}"
ALERT_EMAIL="${ALERT_EMAIL:-weizhongt@google.com}"
ALERT_MODE="${ALERT_MODE:-all}"
DRY_RUN=false
SKIP_BUILD=false
ONLY_SCHEDULER=false
ONLY_ALERTING=false
GRANT_IAM=false

# ==============================================================================
# Help / Usage Function
# ==============================================================================
show_usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Deploy ge-prober as a Google Cloud Run Job, configure Cloud Scheduler trigger, and set up Cloud Monitoring alerts.

Options:
  -p, --project PROJECT_ID          Google Cloud Project ID (default: \$GCP_PROJECT_ID or 'weizhong-project03')
  -r, --region REGION               Google Cloud Region (default: \$GCP_REGION or 'us-central1')
  -e, --engine-id ENGINE_ID         Gemini Enterprise Engine ID (default: \$GE_ENGINE_ID)
  -l, --location LOCATION           Gemini Enterprise Engine Location (default: \$GE_LOCATION or 'global')
  -j, --job-name JOB_NAME           Cloud Run Job name (default: 'ge-prober-daily')
  -n, --scheduler-name NAME         Cloud Scheduler Job name (default: 'trigger-<JOB_NAME>')
  -s, --schedule CRON_EXPR          Cron schedule expression (default: \$SCHEDULE_CRON or '0 9,17 * * *')
  -z, --time-zone TIMEZONE          Time zone for schedule (default: \$TIME_ZONE or 'Asia/Singapore')
  -a, --service-account EMAIL       Service account email for invocation (default: \$SCHEDULER_SA_EMAIL or active gcloud account)
  -m, --alert-email EMAIL           Recipient email for Cloud Monitoring alerts (default: \$ALERT_EMAIL or 'weizhongt@google.com')
      --alert-mode MODE             Alert mode: 'all' (summary of all runs) or 'failure-only' (default: \$ALERT_MODE or 'all')
      --grant-iam                   Automatically grant 'roles/run.invoker' to the service account on the Cloud Run Job
      --dry-run                     Preview planned commands and parameters without making changes
      --skip-build                  Deploy Cloud Run Job using existing image tag without running Cloud Build
      --only-scheduler              Configure or update Cloud Scheduler trigger only (skip container build & job deployment)
      --only-alerting               Configure or update Cloud Monitoring Notification Channel & Alert Policy only
  -h, --help                        Display this help message and exit

Environment Variables:
  GCP_PROJECT_ID, GCP_REGION, GE_ENGINE_ID, GE_LOCATION, JOB_NAME,
  SCHEDULER_JOB_NAME, SCHEDULE_CRON, TIME_ZONE, SCHEDULER_SA_EMAIL,
  ALERT_EMAIL, ALERT_MODE

Examples:
  # Deploy with default settings (twice daily at 09:00 & 17:00 SGT, alert to weizhongt@google.com)
  ./deploy_job.sh

  # Perform a dry-run check with custom project and schedule
  ./deploy_job.sh --dry-run --project="my-gcp-project" --schedule="0 9,17 * * *" --time-zone="Asia/Singapore" --alert-email="team@example.com"

  # Update only Cloud Monitoring alert policy without redeploying job
  ./deploy_job.sh --only-alerting --alert-email="weizhongt@google.com" --alert-mode="all"
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
    -m|--alert-email)
      ALERT_EMAIL="$2"
      shift 2
      ;;
    --alert-email=*)
      ALERT_EMAIL="${1#*=}"
      shift
      ;;
    --alert-mode)
      ALERT_MODE="$2"
      shift 2
      ;;
    --alert-mode=*)
      ALERT_MODE="${1#*=}"
      shift
      ;;
    --grant-iam)
      GRANT_IAM=true
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
    --only-alerting)
      ONLY_ALERTING=true
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

if [[ "${ALERT_MODE}" != "all" && "${ALERT_MODE}" != "failure-only" ]]; then
  echo "Error: Invalid --alert-mode '${ALERT_MODE}'. Must be 'all' or 'failure-only'." >&2
  exit 1
fi

# Resolve default scheduler job name if not explicitly set
if [[ -z "${SCHEDULER_JOB}" ]]; then
  SCHEDULER_JOB="trigger-${JOB_NAME}"
fi

# Resolve service account email if not explicitly provided
if [[ -z "${SERVICE_ACCOUNT}" ]]; then
  if command -v gcloud >/dev/null 2>&1; then
    ACCOUNT_VAL="$(gcloud config get-value account 2>/dev/null || true)"
    if [[ "${ACCOUNT_VAL}" == *".gserviceaccount.com" ]]; then
      SERVICE_ACCOUNT="${ACCOUNT_VAL}"
    else
      DEFAULT_SA="$(gcloud iam service-accounts list --project="${PROJECT_ID}" --filter="displayName:'Default compute service account' OR email:compute@developer.gserviceaccount.com" --format="value(email)" 2>/dev/null | head -n 1 || true)"
      if [[ -n "${DEFAULT_SA}" ]]; then
        SERVICE_ACCOUNT="${DEFAULT_SA}"
      fi
    fi
  fi
  if [[ -z "${SERVICE_ACCOUNT}" ]]; then
    SERVICE_ACCOUNT="default-service-account@${PROJECT_ID}.iam.gserviceaccount.com"
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
echo "Alert Email        : ${ALERT_EMAIL}"
echo "Alert Mode         : ${ALERT_MODE}"
echo "Execution URI      : ${URI}"
echo "Grant IAM Invoker  : ${GRANT_IAM}"
echo "Skip Build         : ${SKIP_BUILD}"
echo "Only Scheduler     : ${ONLY_SCHEDULER}"
echo "Only Alerting      : ${ONLY_ALERTING}"
echo "================================================================================"

# ==============================================================================
# Dry Run Execution Plan
# ==============================================================================
if [[ "${DRY_RUN}" == true ]]; then
  echo "Planned Operations:"
  if [[ "${ONLY_SCHEDULER}" == false && "${ONLY_ALERTING}" == false ]]; then
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
    if [[ "${ONLY_ALERTING}" == true ]]; then
      echo "1. [Run & Build] (Skipped via --only-alerting)"
    else
      echo "1. [Run & Build] (Skipped via --only-scheduler)"
    fi
  fi

  if [[ "${ONLY_ALERTING}" == false ]]; then
    echo "3. [Scheduler] Configuring Cloud Scheduler trigger (${SCHEDULER_JOB}):"
    echo "   gcloud scheduler jobs create http \"${SCHEDULER_JOB}\" (or update) \\"
    echo "     --project=\"${PROJECT_ID}\" \\"
    echo "     --location=\"${REGION}\" \\"
    echo "     --schedule=\"${SCHEDULE_CRON}\" \\"
    echo "     --time-zone=\"${TIME_ZONE}\" \\"
    echo "     --uri=\"${URI}\" \\"
    echo "     --http-method=POST \\"
    echo "     --oauth-service-account-email=\"${SERVICE_ACCOUNT}\""

    if [[ "${GRANT_IAM}" == true ]]; then
      echo "4. [IAM Binding] Granting roles/run.invoker to ${SERVICE_ACCOUNT}:"
      echo "   gcloud run jobs add-iam-policy-binding \"${JOB_NAME}\" \\"
      echo "     --project=\"${PROJECT_ID}\" \\"
      echo "     --region=\"${REGION}\" \\"
      echo "     --member=\"serviceAccount:${SERVICE_ACCOUNT}\" \\"
      echo "     --role=\"roles/run.invoker\""
    else
      echo "4. [IAM Advisory] Ensure ${SERVICE_ACCOUNT} has 'roles/run.invoker' permission."
    fi
  else
    echo "3. [Scheduler & IAM] (Skipped via --only-alerting)"
  fi

  if [[ "${ONLY_SCHEDULER}" == false && -n "${ALERT_EMAIL}" ]]; then
    echo "5. [Cloud Monitoring] Configuring Cloud Monitoring Notification Channel & Alert Policy (${ALERT_EMAIL}):"
    echo "   gcloud beta monitoring channels create (or reuse) \\"
    echo "     --project=\"${PROJECT_ID}\" \\"
    echo "     --display-name=\"ge-prober Notification (${ALERT_EMAIL})\" \\"
    echo "     --type=\"email\" \\"
    echo "     --channel-labels=\"email_address=${ALERT_EMAIL}\""
    if [[ "${ALERT_MODE}" == "all" ]]; then
      echo "   gcloud monitoring policies create --policy-from-file=... \\"
      echo "     --project=\"${PROJECT_ID}\" \\"
      echo "     --notification-channels=\"<CHANNEL_ID>\" \\"
      echo "     --display-name=\"[Daily Report] Gemini Enterprise Smoke Prober Results (${JOB_NAME})\""
    else
      echo "   gcloud monitoring policies create --policy-from-file=... \\"
      echo "     --project=\"${PROJECT_ID}\" \\"
      echo "     --notification-channels=\"<CHANNEL_ID>\" \\"
      echo "     --display-name=\"[ALERT] Gemini Enterprise Smoke Prober Failure (${JOB_NAME})\" \\"
      echo "     --condition-display-name=\"Cloud Run Job execution failed\" \\"
      echo "     --condition-filter=\"resource.type = \\\"cloud_run_job\\\" AND resource.labels.job_name = \\\"${JOB_NAME}\\\" AND metric.type = \\\"run.googleapis.com/job/completed_execution_count\\\" AND metric.labels.result = \\\"failed\\\"\" \\"
      echo "     --aggregation-alignment-period=\"300s\" \\"
      echo "     --aggregation-per-series-aligner=\"ALIGN_DELTA\" \\"
      echo "     --aggregation-cross-series-reducer=\"REDUCE_SUM\" \\"
      echo "     --condition-threshold-value=0 \\"
      echo "     --condition-threshold-comparison=\"COMPARISON_GT\" \\"
      echo "     --combiner=\"OR\""
    fi
  fi
  echo ""
  echo "✅ Dry-run validation passed."
  exit 0
fi

# ==============================================================================
# Step 1: Container Build
# ==============================================================================
if [[ "${ONLY_SCHEDULER}" == false && "${ONLY_ALERTING}" == false ]]; then
  if [[ "${SKIP_BUILD}" == false ]]; then
    echo "📦 [1/4] Building container via Google Cloud Build..."
    gcloud builds submit --project="${PROJECT_ID}" --tag="${IMAGE_TAG}" .
  else
    echo "⏩ [1/4] Skipping container build (--skip-build specified)."
  fi

  # ==============================================================================
  # Step 2: Deploy Cloud Run Job
  # ==============================================================================
  echo "⚡ [2/4] Deploying Cloud Run Job ${JOB_NAME}..."
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
if [[ "${ONLY_ALERTING}" == false ]]; then
  echo "⏰ [3/4] Configuring Cloud Scheduler job ${SCHEDULER_JOB}..."
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

  # ==============================================================================
  # Optional IAM Role Grant
  # ==============================================================================
  if [[ "${GRANT_IAM}" == true ]]; then
    echo "🔑 Granting 'roles/run.invoker' to ${SERVICE_ACCOUNT} on job ${JOB_NAME}..."
    gcloud run jobs add-iam-policy-binding "${JOB_NAME}" \
      --project="${PROJECT_ID}" \
      --region="${REGION}" \
      --member="serviceAccount:${SERVICE_ACCOUNT}" \
      --role="roles/run.invoker"
  fi
fi

# ==============================================================================
# Step 4: Configure Cloud Monitoring Notification Channel & Alert Policy
# ==============================================================================
if [[ "${ONLY_SCHEDULER}" == false && -n "${ALERT_EMAIL}" ]]; then
  echo "🔔 [4/4] Configuring Cloud Monitoring Notification Channel & Alert Policy for ${ALERT_EMAIL}..."
  EXISTING_CHANNEL="$(gcloud beta monitoring channels list --project="${PROJECT_ID}" --filter="type=email AND labels.email_address=\"${ALERT_EMAIL}\"" --format="value(name)" 2>/dev/null | head -n 1 || true)"
  if [[ -n "${EXISTING_CHANNEL}" ]]; then
    CHANNEL_ID="${EXISTING_CHANNEL}"
    echo "Found existing notification channel: ${CHANNEL_ID}"
  else
    echo "Creating new email notification channel for ${ALERT_EMAIL}..."
    CHANNEL_ID="$(gcloud beta monitoring channels create \
      --project="${PROJECT_ID}" \
      --display-name="ge-prober Notification (${ALERT_EMAIL})" \
      --type="email" \
      --channel-labels="email_address=${ALERT_EMAIL}" \
      --format="value(name)")"
    echo "Created notification channel: ${CHANNEL_ID}"
  fi

  if [[ "${ALERT_MODE}" == "all" ]]; then
    POLICY_NAME="[Daily Report] Gemini Enterprise Smoke Prober Results (${JOB_NAME})"
    echo "Configuring log-based alert policy for all completions: ${POLICY_NAME}..."
    EXISTING_POLICY="$(gcloud monitoring policies list --project="${PROJECT_ID}" --filter="displayName:\"${POLICY_NAME}\"" --format="value(name)" 2>/dev/null | head -n 1 || true)"
    if [[ -z "${EXISTING_POLICY}" ]]; then
      TMP_POLICY_JSON="$(mktemp)"
      cat <<EOF > "${TMP_POLICY_JSON}"
{
  "displayName": "${POLICY_NAME}",
  "documentation": {
    "content": "### 📊 Gemini Enterprise Daily Prober Run Summary\n\n**Test Results & Health Score:**\n> \${log.extracted_label.prober_summary}\n\n---\n*Click the Incident & Log links below to view detailed per-probe execution traces.*",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Prober summary reported",
      "conditionMatchedLog": {
        "filter": "resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"${JOB_NAME}\" AND textPayload:\"PROBER SUMMARY & HEALTH SCORE\"",
        "labelExtractors": {
          "prober_summary": "EXTRACT(textPayload)"
        }
      }
    }
  ],
  "alertStrategy": {
    "notificationRateLimit": {
      "period": "300s"
    },
    "autoClose": "1800s"
  },
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": [
    "${CHANNEL_ID}"
  ]
}
EOF
      gcloud monitoring policies create --policy-from-file="${TMP_POLICY_JSON}" --project="${PROJECT_ID}"
      rm -f "${TMP_POLICY_JSON}"
    else
      echo "Alert policy already exists: ${EXISTING_POLICY}"
    fi
  else
    POLICY_NAME="[ALERT] Gemini Enterprise Smoke Prober Failure (${JOB_NAME})"
    echo "Configuring metric-based failure alert policy: ${POLICY_NAME}..."
    EXISTING_POLICY="$(gcloud monitoring policies list --project="${PROJECT_ID}" --filter="displayName:\"${POLICY_NAME}\"" --format="value(name)" 2>/dev/null | head -n 1 || true)"
    if [[ -z "${EXISTING_POLICY}" ]]; then
      TMP_POLICY_JSON="$(mktemp)"
      cat <<EOF > "${TMP_POLICY_JSON}"
{
  "displayName": "${POLICY_NAME}",
  "documentation": {
    "content": "Gemini Enterprise smoke test prober execution failure on job ${JOB_NAME}.",
    "mimeType": "text/markdown"
  },
  "conditions": [
    {
      "displayName": "Cloud Run Job execution failed",
      "conditionThreshold": {
        "filter": "resource.type = \"cloud_run_job\" AND resource.labels.job_name = \"${JOB_NAME}\" AND metric.type = \"run.googleapis.com/job/completed_execution_count\" AND metric.labels.result = \"failed\"",
        "aggregations": [
          {
            "alignmentPeriod": "300s",
            "perSeriesAligner": "ALIGN_DELTA",
            "crossSeriesReducer": "REDUCE_SUM"
          }
        ],
        "comparison": "COMPARISON_GT",
        "thresholdValue": 0,
        "duration": "0s",
        "trigger": {
          "count": 1
        }
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": [
    "${CHANNEL_ID}"
  ]
}
EOF
      gcloud monitoring policies create --policy-from-file="${TMP_POLICY_JSON}" --project="${PROJECT_ID}"
      rm -f "${TMP_POLICY_JSON}"
    else
      echo "Alert policy already exists: ${EXISTING_POLICY}"
    fi
  fi
fi

echo "================================================================================"
echo "✅ Deployment complete! To execute manually:"
echo "   gcloud run jobs execute ${JOB_NAME} --project=${PROJECT_ID} --region=${REGION}"
echo ""
if [[ -n "${ALERT_EMAIL}" ]]; then
  echo "📧 Email Notifications : Configured for '${ALERT_EMAIL}' (mode: ${ALERT_MODE})"
fi
echo "ℹ️  IAM Advisory: Ensure '${SERVICE_ACCOUNT}' has 'roles/run.invoker' on job '${JOB_NAME}':"
echo "   gcloud run jobs add-iam-policy-binding ${JOB_NAME} --project=${PROJECT_ID} --region=${REGION} --member=serviceAccount:${SERVICE_ACCOUNT} --role=roles/run.invoker"
echo "================================================================================"
