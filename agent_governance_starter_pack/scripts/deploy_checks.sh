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

# Test agy_guard.sh
GUARD_TEST1="$(echo '{"toolCall":{"args":{"CommandLine":"/tmp/geap-skill-test/scripts/doctor.sh --project foo"}}}' | bash "$(dirname "${BASH_SOURCE[0]}")/agy_guard.sh")"
[[ "${GUARD_TEST1}" == *"auto_approve"* ]] || fail "agy_guard.sh did not auto_approve absolute doctor.sh: ${GUARD_TEST1}"
GUARD_TEST2="$(echo '{"toolCall":{"args":{"CommandLine":"bash /tmp/geap-skill-test/scripts/configure.sh --tier 3 --mode DRY_RUN"}}}' | bash "$(dirname "${BASH_SOURCE[0]}")/agy_guard.sh")"
[[ "${GUARD_TEST2}" == *"auto_approve"* ]] || fail "agy_guard.sh did not auto_approve bash configure.sh: ${GUARD_TEST2}"
TP="$("$(dirname "${BASH_SOURCE[0]}")/check_tool_policy.sh" 2>&1)" || fail "tool policy: ${TP#TOOL_POLICY: }"
TP2="$("$(dirname "${BASH_SOURCE[0]}")/check_tool_policy.sh" "${ROOT}/mcp-server/tool_spec.json" "${ROOT}/policies/multi_agent_iap_policy.example.yaml" 2>&1)" || fail "multi-agent tool policy: ${TP2#TOOL_POLICY: }"
echo "DEPLOY_CHECKS: PASS (init ok, fmt ok, validate ok, test ${SUMMARY}, tool policy ok, multi-agent policy ok)"

# Test flag consistency
if "./scripts/adoption_plan.sh" --prefix foo 2>&1 | grep -q "unknown argument --prefix"; then
  fail "adoption_plan.sh rejected --prefix"
fi

BIND_OUT=$("./scripts/bind_existing_agent.sh" --project p --region r --agent projects/foo/locations/bar/reasoningEngines/my-agent --egress-gateway projects/foo/locations/bar/agentGateways/my-gw --dry-run 2>&1 || true)
if [[ "${BIND_OUT}" == *"unknown argument"* ]]; then
  fail "bind_existing_agent.sh rejected flags"
fi
if [[ "${BIND_OUT}" != *"Reasoning Engine my-agent"* ]]; then
  fail "bind_existing_agent.sh did not strip agent resource name prefix: ${BIND_OUT}"
fi

rm -f "${LOG}"
