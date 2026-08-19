#!/usr/bin/env bash
# Test suite for scripts/e2e_cloud_pipeline.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIPELINE_SCRIPT="${SCRIPT_DIR}/e2e_cloud_pipeline.sh"
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
echo "🧪 RUNNING E2E CLOUD PIPELINE SCRIPT TEST SUITE"
echo "================================================================================"

# 1. Help flag test
echo "Test 1: --help flag"
HELP_OUT=$(bash "${PIPELINE_SCRIPT}" --help)
assert_contains "${HELP_OUT}" "Usage:" "Help output contains usage"
assert_contains "${HELP_OUT}" "--track-id" "Help output describes --track-id"
assert_contains "${HELP_OUT}" "--dry-run" "Help output describes --dry-run"

# 2. Dry run test with explicit parameters
echo "Test 2: --dry-run mode"
DRY_OUT=$(bash "${PIPELINE_SCRIPT}" --dry-run --project=test-project --region=asia-southeast1 --job-name=test-job --track-id=automated_cloud_e2e_pipeline_and_log_artifacts_20260819)
assert_contains "${DRY_OUT}" "[DRY RUN]" "Dry run banner output"
assert_contains "${DRY_OUT}" "test-project" "Project resolved in dry run"
assert_contains "${DRY_OUT}" "asia-southeast1" "Region resolved in dry run"
assert_contains "${DRY_OUT}" "test-job" "Job name resolved in dry run"
assert_contains "${DRY_OUT}" "conductor/tracks/automated_cloud_e2e_pipeline_and_log_artifacts_20260819/execution.log" "Track log destination resolved"

# 3. Invalid flag rejection
echo "Test 3: Invalid flag rejection"
assert_exit_code "bash '${PIPELINE_SCRIPT}' --invalid-flag" 1 "Invalid flag exits with code 1"

echo "================================================================================"
echo "📊 RESULTS: ${TESTS_PASSED}/${TESTS_RUN} tests passed"
echo "================================================================================"
