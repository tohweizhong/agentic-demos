---
name: geap-audit-tools
description: Lint mcp-server/tool_spec.json against policies/iap_access_policy.yaml to verify that every non-read-only tool is governed.
---

# Skill: geap-audit-tools

Run `scripts/check_tool_policy.sh` before deploying MCP tool updates or promoting IAP policies to `ENFORCE`.

## Steps

1. Run `scripts/check_tool_policy.sh` from `geap_starter_pack/`.
2. Inspect the JSON output:
   - `read_only_tools`: tools where `annotations.readOnlyHint` is `true` in `mcp-server/tool_spec.json`.
   - `governed_non_readonly_tools`: write or mutating tools that have an explicit rule in `policies/iap_access_policy.yaml`.
   - `ungoverned_non_readonly_tools`: write or mutating tools missing an explicit rule in `policies/iap_access_policy.yaml`.
3. If `status` is `FAIL`, add an explicit rule for each ungoverned tool in `policies/iap_access_policy.yaml` before running `terraform apply`.
