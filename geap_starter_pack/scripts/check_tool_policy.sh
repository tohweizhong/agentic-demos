#!/usr/bin/env bash
# Offline linter for MCP tool specs and IAP V2 access policies.
#
# Checks that every tool in mcp-server/tool_spec.json where
# annotations.readOnlyHint is not true is explicitly governed in
# policies/iap_access_policy.yaml.
#
# Usage:
#   scripts/check_tool_policy.sh [--tool-spec FILE] [--policy FILE]
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need jq

TOOL_SPEC="${ROOT}/mcp-server/tool_spec.json"
POLICY_FILE="${ROOT}/policies/iap_access_policy.yaml"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool-spec)
      TOOL_SPEC="$2"
      shift 2
      ;;
    --policy)
      POLICY_FILE="$2"
      shift 2
      ;;
    *)
      echo "Usage: $0 [--tool-spec FILE] [--policy FILE]" >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "${TOOL_SPEC}" ]]; then
  echo "ERROR: Tool spec file not found: ${TOOL_SPEC}" >&2
  exit 2
fi
if [[ ! -f "${POLICY_FILE}" ]]; then
  echo "ERROR: IAP policy file not found: ${POLICY_FILE}" >&2
  exit 2
fi

WRITE_TOOLS="$(jq -r '.tools[] | select((.annotations.readOnlyHint // false) != true) | .name' "${TOOL_SPEC}")"
READ_TOOLS="$(jq -r '.tools[] | select((.annotations.readOnlyHint // false) == true) | .name' "${TOOL_SPEC}")"

UNGOVERNED=()
GOVERNED=()

for tool in ${WRITE_TOOLS}; do
  if grep -q -E "destination\.agent_registry\.mcp_server\.tool\.name[[:space:]]*==[[:space:]]*'${tool}'" "${POLICY_FILE}"; then
    GOVERNED+=("${tool}")
  else
    UNGOVERNED+=("${tool}")
  fi
done

READ_JSON="$(printf '%s\n' "${READ_TOOLS}" | sed '/^$/d' | jq -R . | jq -s .)"
GOVERNED_JSON="$(printf '%s\n' "${GOVERNED[@]:-}" | sed '/^$/d' | jq -R . | jq -s .)"
UNGOVERNED_JSON="$(printf '%s\n' "${UNGOVERNED[@]:-}" | sed '/^$/d' | jq -R . | jq -s .)"

STATUS="PASS"
if [[ "${#UNGOVERNED[@]}" -gt 0 ]]; then
  STATUS="FAIL"
fi

jq -n \
  --arg status "${STATUS}" \
  --arg tool_spec "${TOOL_SPEC}" \
  --arg policy_file "${POLICY_FILE}" \
  --argjson read_only_tools "${READ_JSON}" \
  --argjson governed_non_readonly_tools "${GOVERNED_JSON}" \
  --argjson ungoverned_non_readonly_tools "${UNGOVERNED_JSON}" \
  '{
    status: $status,
    tool_spec: $tool_spec,
    policy_file: $policy_file,
    read_only_tools: $read_only_tools,
    governed_non_readonly_tools: $governed_non_readonly_tools,
    ungoverned_non_readonly_tools: $ungoverned_non_readonly_tools
  }'

if [[ "${STATUS}" != "PASS" ]]; then
  exit 1
fi
