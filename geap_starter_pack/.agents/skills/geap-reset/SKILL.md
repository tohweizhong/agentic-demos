---
name: geap-reset
description: Reset the GEAP starter pack demo back to DRY_RUN mode and verify that the write tool passes again.
---

# Skill: geap-reset

Follow `runbooks/reset_demo.md` to return the mini build to its starting demo state.

## Steps

1. Set `iap_enforcement_mode = "DRY_RUN"` in `terraform/terraform.tfvars`.
2. Run `terraform plan -out=tfplan` in `terraform/` and show the single resource change (`google_iam_projects_policy_binding.agent_egress`) to the user for approval.
3. After approval, run `terraform apply tfplan` and wait 3 minutes for the gateway policy to propagate.
4. Reset any modified work item (`ITEM-001`, `ITEM-002`, or `ITEM-003`) via `scripts/ask_agent.sh`.
