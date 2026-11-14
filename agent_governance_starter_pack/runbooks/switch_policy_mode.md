# Runbook: switch policy mode and reset state

## Purpose

Switch the IAP V2 policy binding between `DRY_RUN` (shadow mode for onboarding new agents or tools)
and `ENFORCE` (active access control), and reset the sample MCP server in-memory state when needed.

## Idle cost

The foundation keeps warm instances running so tool calls do not time out:

- The agent on Agent Runtime sets `min_instances = 1` in `terraform/agent.tf` (about USD 0.16 per
  hour or USD 3.80 per day in `us-central1`).
- The MCP server on Cloud Run sets `min_instance_count = 1` in `terraform/registry.tf` (about
  USD 0.08 per hour or USD 1.90 per day). A cold start takes longer than the MCP timeout of the
  agent.

The Agent Gateway, the authz extensions, and Model Armor also have usage costs. Check the Billing
report for the project, grouped by SKU. Run `scripts/cleanup.sh` when you no longer need the
environment.

## Before you start

- The foundation is deployed with `enable_egress_gateway = true`.
- Schedule a maintenance window if agents serve live traffic. A change to the gateway policy can
  interrupt agent traffic for a few minutes.

## Steps

1. Set the target enforcement mode with `scripts/configure.sh`. Do not edit
   `terraform/terraform.tfvars` by hand. The script keeps the tier and every other value:

   ```bash
   # Use DRY_RUN to observe traffic when you onboard a new agent or tool.
   # Use ENFORCE to block denied tool calls at the egress gateway.
   scripts/configure.sh --set-mode ENFORCE --dry-run   # check the CONFIGURE line: only mode changes
   scripts/configure.sh --set-mode ENFORCE
   ```

Before you set `ENFORCE`, run the read-only promotion readiness report. It lists the tools that
`ENFORCE` blocks (from the policy file) and the logged `DRY_RUN` decisions that would be blocked:

```bash
scripts/check_promotion.sh --lookback 24h   # last line: PROMOTION: READY or REVIEW
```

2. Apply the change:

   ```bash
   terraform -chdir=terraform plan -out=tfplan    # expect: 1 to change (google_network_services_authz_extension.iap[0])
   terraform -chdir=terraform apply tfplan
   ```

   The apply takes 2 to 4 minutes. Wait 3 more minutes after `terraform apply` finishes so the
   gateway data plane loads the new mode.

   Known problem: an update to the gateway authz policy can fail with `ABORTED` ("There is another
   ongoing operation for the same AgentGateway"). If this occurs, detach the target policy, apply the
   update, and re-attach the policy. While the policy is detached, the gateway denies all agent
   traffic.

3. Optional: reset the sample MCP server in-memory data. A new Cloud Run revision starts with the
   initial seed data (`ITEM-001` = `open`, `ITEM-002` = `in_progress`, `ITEM-003` = `open`):

   ```bash
   PROJECT=$(terraform -chdir=terraform output -raw project_id)
   REGION=$(terraform -chdir=terraform output -raw region)
   gcloud run services update geap-work-items --project="${PROJECT}" --region="${REGION}" \
     --update-labels="state-reset=$(date -u +%Y%m%d%H%M%S)"
   ```

   `terraform/registry.tf` ignores the `state-reset` label (`ignore_changes`), so the next
   `terraform plan` shows no drift. If you changed `name_prefix`, use `<name_prefix>-work-items` as
   the service name.

4. Start a fresh session for your next test. Run `scripts/ask_agent.sh` without `-s`, or pass a new
   `-u` user ID.

## Check the result

1. Run `terraform -chdir=terraform output iap_enforcement_mode` and confirm that it matches your
   target mode (`DRY_RUN` or `ENFORCE`).
2. Ask the agent: `scripts/ask_agent.sh "What is the status of ITEM-001?"` The answer is `open`.
3. Ask the agent: `scripts/ask_agent.sh "Set ITEM-003 to closed."`
   - In `DRY_RUN`, the tool call passes and updates the item.
   - In `ENFORCE`, the egress gateway blocks `update_status`, the agent reports a tool error, and no
     request reaches the Cloud Run request log.
