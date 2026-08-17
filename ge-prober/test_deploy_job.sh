#!/usr/bin/env bash
# Test suite for deploy_job.sh parameterization and dry-run functionality
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_SCRIPT="${SCRIPT_DIR}/deploy_job.sh"
TESTS_RUN=0
TESTS_PASSED=0

assert_contains() {
  local output="$1"
  local expected="$2"
  local test_name="$3"
  TESTS_RUN=$((TESTS_RUN + 1))
  if echo "${output}" | grep -Fq -- "${expected}"; then
    echo "  ✅ PASS: ${test_name}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo "  ❌ FAIL: ${test_name}"
    echo "     Expected to contain: '${expected}'"
    echo "     Actual output: ${output}"
    return 1
  fi
}

assert_not_contains() {
  local output="$1"
  local unexpected="$2"
  local test_name="$3"
  TESTS_RUN=$((TESTS_RUN + 1))
  if ! echo "${output}" | grep -Fq -- "${unexpected}"; then
    echo "  ✅ PASS: ${test_name}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo "  ❌ FAIL: ${test_name}"
    echo "     Did not expect to contain: '${unexpected}'"
    echo "     Actual output: ${output}"
    return 1
  fi
}

assert_exit_code() {
  local cmd="$1"
  local expected_code="$2"
  local test_name="$3"
  TESTS_RUN=$((TESTS_RUN + 1))
  set +e
  eval "${cmd}" >/dev/null 2>&1
  local actual_code=$?
  set -e
  if [ "${actual_code}" -eq "${expected_code}" ]; then
    echo "  ✅ PASS: ${test_name} (exit code ${actual_code})"
    TESTS_PASSED=$((TESTS_PASSED + 1))
  else
    echo "  ❌ FAIL: ${test_name} (expected exit code ${expected_code}, got ${actual_code})"
    return 1
  fi
}

echo "================================================================================"
echo "🧪 Running deploy_job.sh Test Suite"
echo "================================================================================"

# 1. Help flag
echo "Test 1: Help Flag"
HELP_OUT="$("${DEPLOY_SCRIPT}" --help || true)"
assert_contains "${HELP_OUT}" "Usage:" "Help outputs usage instructions"
assert_contains "${HELP_OUT}" "--schedule" "Help describes --schedule flag"
assert_contains "${HELP_OUT}" "--time-zone" "Help describes --time-zone flag"
assert_contains "${HELP_OUT}" "--service-account" "Help describes --service-account flag"
assert_contains "${HELP_OUT}" "--dry-run" "Help describes --dry-run flag"
assert_contains "${HELP_OUT}" "--only-scheduler" "Help describes --only-scheduler flag"

# 2. Dry Run Default Values
echo "Test 2: Dry Run with Defaults"
DRY_OUT="$("${DEPLOY_SCRIPT}" --dry-run)"
assert_contains "${DRY_OUT}" "DRY RUN MODE" "Dry run banner displayed"
assert_contains "${DRY_OUT}" "0 1 * * *" "Default schedule cron is 0 1 * * *"
assert_contains "${DRY_OUT}" "Asia/Singapore" "Default time zone is Asia/Singapore"
assert_contains "${DRY_OUT}" "gcloud scheduler jobs" "Shows scheduler job command"

# 3. CLI Flag Overrides
echo "Test 3: CLI Flag Overrides"
FLAG_OUT="$("${DEPLOY_SCRIPT}" --dry-run \
  --project="custom-proj" \
  --region="europe-west1" \
  --engine-id="custom-eng" \
  --job-name="custom-prober" \
  --scheduler-name="custom-trigger" \
  --schedule="30 2 * * *" \
  --time-zone="UTC" \
  --service-account="custom-sa@custom-proj.iam.gserviceaccount.com")"
assert_contains "${FLAG_OUT}" "custom-proj" "Custom project ID resolved"
assert_contains "${FLAG_OUT}" "europe-west1" "Custom region resolved"
assert_contains "${FLAG_OUT}" "custom-eng" "Custom engine ID resolved"
assert_contains "${FLAG_OUT}" "custom-prober" "Custom job name resolved"
assert_contains "${FLAG_OUT}" "custom-trigger" "Custom scheduler job name resolved"
assert_contains "${FLAG_OUT}" "30 2 * * *" "Custom schedule cron resolved"
assert_contains "${FLAG_OUT}" "UTC" "Custom time zone resolved"
assert_contains "${FLAG_OUT}" "custom-sa@custom-proj.iam.gserviceaccount.com" "Custom service account resolved"

# 4. Environment Variable Overrides
echo "Test 4: Environment Variable Overrides"
ENV_OUT="$(GCP_PROJECT_ID="env-proj" \
  GCP_REGION="asia-east1" \
  SCHEDULE_CRON="0 4 * * *" \
  TIME_ZONE="America/New_York" \
  SCHEDULER_SA_EMAIL="env-sa@env-proj.iam.gserviceaccount.com" \
  "${DEPLOY_SCRIPT}" --dry-run)"
assert_contains "${ENV_OUT}" "env-proj" "Environment variable project ID resolved"
assert_contains "${ENV_OUT}" "asia-east1" "Environment variable region resolved"
assert_contains "${ENV_OUT}" "0 4 * * *" "Environment variable cron resolved"
assert_contains "${ENV_OUT}" "America/New_York" "Environment variable timezone resolved"
assert_contains "${ENV_OUT}" "env-sa@env-proj.iam.gserviceaccount.com" "Environment variable service account resolved"

# 5. CLI Flags Take Precedence Over Environment Variables
echo "Test 5: CLI Precedence over Environment Variables"
PREC_OUT="$(GCP_PROJECT_ID="env-proj" SCHEDULE_CRON="0 4 * * *" \
  "${DEPLOY_SCRIPT}" --dry-run --project="cli-proj" --schedule="0 6 * * *")"
assert_contains "${PREC_OUT}" "cli-proj" "CLI flag overrides env var for project ID"
assert_contains "${PREC_OUT}" "0 6 * * *" "CLI flag overrides env var for schedule cron"

# 6. Only Scheduler Mode
echo "Test 6: Only Scheduler Mode"
ONLY_SCHED_OUT="$("${DEPLOY_SCRIPT}" --dry-run --only-scheduler)"
assert_contains "${ONLY_SCHED_OUT}" "Configuring Cloud Scheduler trigger" "Scheduler trigger step present"
assert_not_contains "${ONLY_SCHED_OUT}" "gcloud builds submit" "Build step skipped in --only-scheduler"
assert_not_contains "${ONLY_SCHED_OUT}" "gcloud run jobs deploy" "Run deploy step skipped in --only-scheduler"

# 7. Invalid Flag
echo "Test 7: Error on Unknown Flag"
assert_exit_code "'${DEPLOY_SCRIPT}' --unknown-flag" 1 "Unknown flag returns exit code 1"

echo "================================================================================"
echo "📊 Results: ${TESTS_PASSED}/${TESTS_RUN} passed"
echo "================================================================================"

if [ "${TESTS_PASSED}" -ne "${TESTS_RUN}" ]; then
  exit 1
fi
