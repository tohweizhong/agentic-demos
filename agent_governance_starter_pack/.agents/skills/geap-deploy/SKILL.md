---
name: geap-deploy
description: Package the reference agent, run offline tests, generate a Terraform plan, and pause for human approval before applying.
---

# Skill: geap-deploy

Deploy or update the agent governance starter pack mini build with a mandatory approval gate before `terraform apply`.

## Steps

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
