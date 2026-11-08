# Runbook: reset the demo

## Purpose

Return the mini build to the start state of the 10-minute demo: the IAP policy is in `DRY_RUN`,
the sample data is new, and the next question starts a new session.

## Idle cost

The mini build stays up between demos, so it has a cost when nobody uses it. Two settings keep
instances running all the time:

- The agent on Agent Runtime: `min_instances = 1` in `terraform/agent.tf`.
- The MCP server on Cloud Run: `min_instance_count = 1` in `terraform/registry.tf`. A cold start
  takes longer than the MCP timeout of the agent.

The Agent Gateway, the authz extensions, and Model Armor can also have a cost. Check the Billing
report for the project, grouped by SKU. Run `scripts/cleanup.sh` after the last demo.

## Before you start

- The mini build is deployed.
- Nobody uses the demo. A change to the gateway policy can block agent traffic for some minutes.

## Steps

1. Set the IAP policy back to `DRY_RUN`. In `terraform/terraform.tfvars`, set:

   ```hcl
   iap_enforcement_mode = "DRY_RUN"
   ```

2. Apply the change:

   ```bash
   cd terraform
   terraform plan -out=tfplan    # expect: 1 to change (the IAP authz extension)
   terraform apply tfplan
   cd ..
   ```

   Known problem: the update can fail with `ABORTED` ("There is another ongoing operation for the
   same AgentGateway"). The codelab runbook in
   [`curated_codelabs/agent-gateway-governance`](../../curated_codelabs/agent-gateway-governance/RUNBOOK.md)
   describes a workaround (step 8, Fix 5). While the policies are missing, the gateway denies all
   agent traffic.

3. Reset the sample data. A new Cloud Run revision starts with the seed data:

   ```bash
   PROJECT=$(terraform -chdir=terraform output -raw project_id)
   REGION=$(terraform -chdir=terraform output -raw region)
   gcloud run services update geap-work-items --project="${PROJECT}" --region="${REGION}" \
     --update-labels="demo-reset=$(date -u +%Y%m%d%H%M%S)"
   ```

   Terraform ignores the `demo-reset` label, so the next `terraform plan` shows no change for it.
   If you changed `name_prefix`, use `<name_prefix>-work-items` as the service name.

4. Use a new session for the next demo. Run `scripts/ask_agent.sh` without `-s`, or with a new
   `-u` user ID.

## Check the result

1. `terraform output iap_enforcement_mode` shows `DRY_RUN`.
2. Ask the agent: "What is the status of ITEM-001?" The answer is `open`.
3. Ask the agent: "Set ITEM-003 to closed." In `DRY_RUN` the call passes.
   `scripts/read_audit_log.sh 10m` shows an IAP entry with `DRY_RUN` true and `GRANTED` false.
4. Run step 3 again, so that ITEM-003 is `open` before the demo starts.

## Restore

There is nothing to restore. To go back to the enforced state, set
`iap_enforcement_mode = "ENFORCE"` and run `terraform apply`.
