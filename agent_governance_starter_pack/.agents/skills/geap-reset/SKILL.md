---
name: geap-reset
description: Switch the agent governance starter pack policy mode back to DRY_RUN and reset the sample MCP server state.
---

# Skill: geap-reset

Follow `runbooks/switch_policy_mode.md` to switch `iap_enforcement_mode` back to `DRY_RUN` and reset the sample work item state.

## Steps

1. Run `scripts/configure.sh --set-mode DRY_RUN --dry-run`. Show the `CONFIGURE:` line word for word. Only `mode` must change. Then run `scripts/configure.sh --set-mode DRY_RUN`. Do not edit `terraform/terraform.tfvars` by hand.
2. Run `terraform -chdir=terraform plan -out=tfplan` and show the single resource change (`google_network_services_authz_extension.iap[0]`) to the user for approval.
3. After approval, run `terraform -chdir=terraform apply tfplan` and wait 3 minutes for the gateway policy to propagate.
4. Reset any modified work item (`ITEM-001`, `ITEM-002`, or `ITEM-003`) via `scripts/ask_agent.sh`.
