---
name: geap-configure
description: Ask the user for each deployment choice (project, region, name prefix, governance tier, domain restricted sharing approach, IAP mode), then write terraform/terraform.tfvars and the region setting in policies/model_armor.yaml. Run it before geap-preflight and geap-deploy.
---

# Skill: geap-configure

Build `terraform/terraform.tfvars` with the user. Ask one question at a time. Explain each choice in
one or two sentences. Show the recommended answer first. Do not guess a value that the user must
choose.

## Rules

- Never write a real project ID, project number, or organization ID into a file that Git tracks.
  `terraform/terraform.tfvars` is ignored by Git. `policies/model_armor.yaml` is tracked, so change
  only its `malicious_uri.enforcement` value, and tell the user not to commit that change.
- Use only read-only commands to find values: `gcloud config get-value project`,
  `gcloud projects describe`, `gcloud projects get-ancestors`, `gcloud org-policies describe`.
- If `terraform/terraform.tfvars` exists, show its current values and ask if the user wants to keep
  or change each one.

## Questions, in this order

0. **New or existing project.** Ask if the project is new (no agents yet) or already has agents, MCP
   servers, or gateways that the starter pack did not create. For an existing project, run the
   `geap-discover` skill after question 1 and show its report. Explain that the starter pack builds
   the vertical path (its own reference agent and controls), and that the lateral steps for the
   existing resources are listed in the report but the tools for them are not built yet (backlog item 30).
1. **Project.** Show the value of `gcloud config get-value project`. Ask the user to confirm it or
   give another project ID. Then find the project number with
   `gcloud projects describe PROJECT_ID --format="value(projectNumber)"` and the organization ID
   with `gcloud projects get-ancestors PROJECT_ID --format="value(id,type)"` (the row with type
   `organization`). Show both and ask the user to confirm.
2. **Region.** Offer these options. Do not show test dates to the user. GUIDE.md "Regions other than us-central1" keeps the test record. The model values below are for your explanation only. `scripts/configure.sh` sets them:
   - `us-central1` (default, tested). Sets `model_id = "gemini-3.8-flash"`,
     `model_location = "global"`, and `malicious_uri.enforcement: ENABLED`.
   - `asia-southeast1` (tested). Sets `model_id = "gemini-3.5-flash"`,
     `model_location = "asia-southeast1"`, and `malicious_uri.enforcement: DISABLED` (Model Armor in
     this region does not support the malicious URI filter).
   - Another region: tell the user that it is not tested, and that Agent Runtime, Agent Gateway,
     Agent Registry, Model Armor, and the Gemini model must all be available there.
3. **Name prefix.** Default `geap`. It must match `^[a-z][a-z0-9-]{1,14}$`. Tell the user that a
   prefix that was used with `scripts/cleanup.sh --purge-all` in the last 7 days fails, because the
   audit log bucket `<prefix>-agent-audit` is soft-deleted.
4. **Governance tier.** Show this table. Also give the link to the tier pyramid in the README, so that the user can see the picture and read it again later: [README: Governance tiers](https://github.com/tohweizhong/agentic-demos/blob/main/agent_governance_starter_pack/README.md#governance-tiers) (local file: `README.md`, section "Governance tiers", image `images/governance_tiers.svg`). Ask the user how to roll out:
   - **Build up one tier at a time (recommended for a first rollout).** Start at Tier 1. After each
     tier is deployed and verified, the user runs `geap-configure` again to move up one tier. This is
     how a customer team learns each control before it adds the next one.
   - **Go to a target tier now.** Ask for a tier from 1 to 5. Tiers add up: a tier includes every
     lower tier. The Terraform checks stop a plan that skips a tier (for example Tier 3 without
     Tier 2).

   Show the table with these short column names, so that it fits in a terminal. Do not use the
   variable names as column headers.

   | Tier | Adds | Registry | Egress | Model Armor | Ingress |
   |---|---|---|---|---|---|
   | 1 | Agent with its own Agent Identity, Cloud Run MCP server, IAM grants, audit log bucket | off | off | off | off |
   | 2 | Agent Registry entries | on | off | off | off |
   | 3 | Egress Agent Gateway with IAP policy V2 | on | on | off | off |
   | 4 | Model Armor on egress | on | on | on | off |
   | 5 | Ingress Agent Gateway with Model Armor on prompts | on | on | on | on |

   Under the table, give this key in one line: Registry = `enable_agent_registry`, Egress =
   `enable_egress_gateway`, Model Armor = `enable_model_armor`, Ingress = `enable_ingress_gateway`
   (on = `true`, off = `false`).

5. **Domain restricted sharing (only for Tier 4 and Tier 5).** Run
   `gcloud org-policies describe iam.allowedPolicyMemberDomains --project=PROJECT_ID --effective`.
   If the policy restricts members, explain that the gateway service account needs 3 Model Armor
   roles and offer the approaches in GUIDE.md Section 3:
   - Approach 2 (recommended for a sandbox): `allow_google_managed_members = true`. Terraform sets a
     project-level policy that allows Google-managed members. The caller needs
     `roles/orgpolicy.policyAdmin`.
   - Approach 1: an organization administrator changes the policy. Keep
     `allow_google_managed_members = false`.
   If the policy does not restrict members, keep `allow_google_managed_members = false`.
6. **IAP enforcement mode (only for Tier 3 and higher).** Recommend `DRY_RUN`: the gateway records
   each decision but does not block. Change to `ENFORCE` later with
   `runbooks/switch_policy_mode.md`.

## Move up one tier

Use this part when `terraform/terraform.tfvars` exists and the user asks to move up a tier.

1. Read the four `enable_*` values and show the current tier.
2. Give the link to the tier pyramid ([README: Governance tiers](https://github.com/tohweizhong/agentic-demos/blob/main/agent_governance_starter_pack/README.md#governance-tiers)). Show what the next tier adds (one row of the table above), what it costs in time (a gateway takes
   about 3 minutes to create, an IAP policy about 3 minutes, and a Reasoning Engine replacement for Tier 3 or Tier 5 takes 8 to 12 minutes, so Tier 3 and Tier 5 take 14 to 18 minutes total), and what it needs:
   - Tier 2: nothing more.
   - Tier 3: nothing more. Ask question 6 (IAP mode). Recommend `DRY_RUN`.
   - Tier 4: ask question 5 (domain restricted sharing).
   - Tier 5: nothing more. If `model_armor_egress_scope` is `auto` (the default), tell the user: at
     Tier 5, egress Model Armor changes from `all_egress` to `mcp_servers`. The ingress gateway then
     screens user prompts and agent replies, and egress screens only the MCP server traffic. The plan
     shows one change on the egress Model Armor policy (host rules). `configure.sh` prints a `NOTE:`
     line about this. Show it word for word.
3. Ask the user to confirm. Then run `scripts/configure.sh --move-up` (add
   `--allow-google-managed-members` or `--mode` only for the answers to questions 5 or 6). The script
   changes only the tier values and keeps the project, region, and prefix.
4. Tell the user that the next step is `geap-deploy`, then `geap-verify`.

## Write the files

Do not write `terraform/terraform.tfvars` or `policies/model_armor.yaml` yourself. The script
`scripts/configure.sh` writes them. It holds the fixed region values (model, model location,
malicious URI filter), so that the values do not depend on the agent.

1. Run the script with `--dry-run` and the answers. Show its `CONFIGURE:` line to the user word for word:
   ```bash
   scripts/configure.sh --project PROJECT_ID --region REGION --prefix PREFIX --tier N \
     --allow-google-managed-members false --mode DRY_RUN --dry-run
   ```
   To move up one tier, use `scripts/configure.sh --move-up --dry-run`.
2. Ask the user to confirm.
3. Run the same command without `--dry-run`. Show the last lines of its output.
4. If the region is `asia-southeast1`, tell the user not to commit `policies/model_armor.yaml`.
5. Tell the user that the next step is `geap-preflight`, then `geap-deploy`.
