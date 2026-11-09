#!/usr/bin/env bash
# Offline check (backlog item 15): every MCP tool that can change data must have
# an explicit rule in the IAP access policy. A tool can change data when its
# readOnlyHint is not true. The check passes when each such tool name appears in
# at least one rule expression of policies/iap_access_policy.yaml.
#
#   scripts/check_tool_policy.sh [TOOL_SPEC_JSON] [POLICY_YAML]
# Prints one line: TOOL_POLICY: PASS (...) or TOOL_POLICY: FAIL (...). Exit 1 on FAIL.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need python3

SPEC="${1:-${ROOT}/mcp-server/tool_spec.json}"
POLICY="${2:-${ROOT}/policies/iap_access_policy.yaml}"

python3 - "${SPEC}" "${POLICY}" <<'PY'
import json, re, sys
spec_path, policy_path = sys.argv[1], sys.argv[2]
tools = json.load(open(spec_path)).get("tools", [])
policy = open(policy_path).read()
# Tool names that the policy names in a CEL condition.
named = set(re.findall(r"tool\.name\s*==\s*'([^']+)'", policy))
named |= set(n for grp in re.findall(r"tool\.name\s+in\s+\[([^\]]+)\]", policy) for n in re.findall(r"'([^']+)'", grp))
write_tools = [t["name"] for t in tools if not t.get("annotations", {}).get("readOnlyHint", False)]
read_tools = [t["name"] for t in tools if t.get("annotations", {}).get("readOnlyHint", False)]
missing = [t for t in write_tools if t not in named]
if missing:
    print(f"TOOL_POLICY: FAIL (tools that can change data with no rule: {', '.join(missing)}; add a rule in {policy_path})")
    sys.exit(1)
print(f"TOOL_POLICY: PASS (write tools with a rule: {', '.join(write_tools) or 'none'}; read-only tools: {', '.join(read_tools) or 'none'})")
PY
