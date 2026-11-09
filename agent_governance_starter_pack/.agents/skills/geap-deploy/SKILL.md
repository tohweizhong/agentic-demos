---
name: geap-deploy
description: Package the reference agent, run offline tests, generate a Terraform plan, and pause for human approval before applying.
---

# Skill: geap-deploy

Deploy or update the agent governance starter pack mini build with a mandatory approval gate before `terraform apply`.

## Steps

0. If `terraform/terraform.tfvars` does not exist, or still has a placeholder (`PROJECT_ID`, `PROJECT_NUMBER`, `ORG_ID`), run the `geap-configure` skill first. Otherwise show the governance tier, region, `name_prefix`, and `iap_enforcement_mode` from the file, and ask the user to confirm them before you continue.
1. Run `scripts/preflight.sh` first. Stop if `status` is `NO_GO`.
2. Build the repeatable agent source archive:
   ```bash
   scripts/package_agent.sh
   ```
3. Run offline checks:
   ```bash
   (cd terraform && terraform fmt -check -recursive && terraform validate && terraform test)
   ```
4. Create the Terraform plan:
   ```bash
   cd terraform && terraform plan -out=tfplan
   ```
5. Report the plan summary (how many resources to add, change, and destroy, plus their types) to the user and **stop**.
6. Run `terraform apply tfplan` only after the user approves the plan summary.
7. Run the apply as a background task. Every 5 minutes, report the elapsed time, the number of resources created so far from the output, and the resource that is being created now. An apply with both gateways takes about 8 to 16 minutes.
