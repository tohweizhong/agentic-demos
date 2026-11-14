---
name: geap-deploy
description: Package the reference agent, run offline tests, generate a Terraform plan, and pause for human approval before applying.
---

# Skill: geap-deploy

Deploy or update the agent governance starter pack mini build with a mandatory approval gate before `terraform apply`.

## Steps

0. If `terraform/terraform.tfvars` does not exist, or still has a placeholder (`PROJECT_ID`, `PROJECT_NUMBER`, `ORG_ID`), run the `geap-configure` skill first. Otherwise show the governance tier, region, `name_prefix`, and `iap_enforcement_mode` from the file, and ask the user to confirm them before you continue.
1. Run `scripts/preflight.sh` and wait for its JSON. Report `status` and the blockers. Stop if `status` is `NO_GO` or `ERROR`. Do not start the next step before the preflight result is in. If a `GO` report from this session is less than 10 minutes old and the settings did not change, you can reuse it and say so.
2. Build the repeatable agent source archive:
   ```bash
   scripts/package_agent.sh
   ```
3. Run the offline checks with one script. It runs `terraform init`, `fmt -check`, `validate`, and `test`, and prints one result line:
   ```bash
   scripts/deploy_checks.sh
   ```
   Show the `DEPLOY_CHECKS:` line to the user word for word. Stop if it is not `DEPLOY_CHECKS: PASS (...)`.
4. Create the Terraform plan. Use `-chdir`, not `cd`, so that a permission rule names `terraform`:
   ```bash
   terraform -chdir=terraform plan -out=tfplan
   ```
5. Report the `DEPLOY_CHECKS:` line and the plan summary (how many resources to add, change, and destroy, plus their types) to the user and **stop**.
6. Run `terraform -chdir=terraform apply tfplan` only after the user approves the plan summary. If the user asks for a result first (for example the test line), show it and wait for a new approval.
7. Run the apply as a background task. Every 5 minutes, report the elapsed time, the number of resources created so far from the output, and the resource that is being created now. An apply with both gateways takes about 8 to 16 minutes.
8. If the apply fails on `google_project_iam_member.gateway_model_armor` with `not in permitted organization`
   after Terraform created the project exception, IAM has not used the exception yet. Do not change the
   settings. Run `gcloud org-policies describe iam.allowedPolicyMemberDomains --project=PROJECT_ID --effective`
   and show the result. When it shows `allowAll: true`, wait 2 minutes, then make a new plan (it must show
   only the 3 grants to add) and ask the user to approve it. Terraform now polls the effective policy and
   waits `org_policy_wait_seconds` (default 120) before the grants, so this case is rare.
