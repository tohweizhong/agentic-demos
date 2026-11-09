#!/usr/bin/env bash
# Runs the offline checks before a plan: terraform init, fmt, validate, test, and
# the tool policy check (scripts/check_tool_policy.sh).
# Prints one result line at the end, so that an agent or a person can read it:
#   DEPLOY_CHECKS: PASS (init ok, fmt ok, validate ok, test 12 passed, 0 failed)
#   DEPLOY_CHECKS: FAIL (<first failed step>)
# Exit code 0 only when every step passes. It does not change anything in the cloud.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need terraform

TF="terraform -chdir=${TF_DIR}"
LOG="$(mktemp)"
fail() { echo "DEPLOY_CHECKS: FAIL ($1). Full output: ${LOG}"; exit 1; }

${TF} init -input=false -no-color >>"${LOG}" 2>&1 || fail "terraform init"
${TF} fmt -check -recursive >>"${LOG}" 2>&1 || fail "terraform fmt -check: run terraform fmt -recursive"
${TF} validate -no-color >>"${LOG}" 2>&1 || fail "terraform validate"
${TF} test -no-color >"${LOG}.test" 2>&1
TEST_RC=$?
cat "${LOG}.test" >>"${LOG}"
SUMMARY="$(grep -Eo '[0-9]+ passed, [0-9]+ failed' "${LOG}.test" | tail -1)"
rm -f "${LOG}.test"
[[ ${TEST_RC} -eq 0 && -n "${SUMMARY}" && "${SUMMARY}" == *", 0 failed" ]] || fail "terraform test: ${SUMMARY:-no summary line}"
TP="$("$(dirname "${BASH_SOURCE[0]}")/check_tool_policy.sh" 2>&1)" || fail "tool policy: ${TP#TOOL_POLICY: }"
TP2="$("$(dirname "${BASH_SOURCE[0]}")/check_tool_policy.sh" "${ROOT}/mcp-server/tool_spec.json" "${ROOT}/policies/multi_agent_iap_policy.example.yaml" 2>&1)" || fail "multi-agent tool policy: ${TP2#TOOL_POLICY: }"
echo "DEPLOY_CHECKS: PASS (init ok, fmt ok, validate ok, test ${SUMMARY}, tool policy ok, multi-agent policy ok)"
rm -f "${LOG}"
