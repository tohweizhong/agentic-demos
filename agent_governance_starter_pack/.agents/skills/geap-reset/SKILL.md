---
name: geap-reset
description: Switch the agent governance starter pack policy mode back to DRY_RUN and reset the sample MCP server state.
---

# Skill: geap-reset

Follow `runbooks/switch_policy_mode.md` to switch `iap_enforcement_mode` back to `DRY_RUN` and reset the sample work item state.

## Steps

1. Set `iap_enforcement_mode = "DRY_RUN"` in `terraform/terraform.tfvars`.
2. Run `terraform plan -out=tfplan` in `terraform/` and show the single resource change (`google_iam_projects_policy_binding.agent_egress`) to the user for approval.
3. After approval, run `terraform apply tfplan` and wait 3 minutes for the gateway policy to propagate.
4. Reset any modified work item (`ITEM-001`, `ITEM-002`, or `ITEM-003`) via `scripts/ask_agent.sh`.
