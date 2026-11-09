# Runbook: Handover Checklist

Use this checklist when the starter pack moves from the build team to the team that runs it
(backlog item 23). Each row needs a named owner and a result. A row with no result is not done.

## 1. Code and state

| # | Check | How to check | Owner | Result |
|---|---|---|---|---|
| 1.1 | The customer repository has the starter pack at a known commit | `git log -1` in the customer clone | | |
| 1.2 | Terraform state is in a remote, versioned backend (not a laptop or Cloud Shell) | `scripts/init_remote_state.sh --apply`, then `terraform -chdir=terraform state list` works from a second machine | | |
| 1.3 | `terraform.tfvars` is stored outside Git and backed up | Location and access list written down | | |
| 1.4 | `scripts/deploy_checks.sh` passes on the handover commit | `DEPLOY_CHECKS: PASS (...)` | | |
| 1.5 | `terraform -chdir=terraform plan` shows no changes | `No changes.` | | |

## 2. Project and organization

| # | Check | How to check | Owner | Result |
|---|---|---|---|---|
| 2.1 | `scripts/preflight.sh` reports `GO` with no false facts | JSON report attached | | |
| 2.2 | The domain restricted sharing exception (Approach 2) is removed after the Model Armor grants | `gcloud org-policies list --project=PROJECT_ID` shows no `iam.allowedPolicyMemberDomains` override | | |
| 2.3 | Organization policy approvals are recorded (for GCC, GovTech approvals) | Approval references written down | | |
| 2.4 | Quotas for Agent Runtime, Agent Gateway, and Model Armor are enough for the planned agents | Quota page or request IDs | | |
| 2.5 | The chosen tier is written down, and each tier above it has a reason to wait | Tier and reason | | |

## 3. Controls

| # | Check | How to check | Owner | Result |
|---|---|---|---|---|
| 3.1 | `geap-verify` (or the GUIDE Section 6 checks) passes for the chosen tier | Results attached | | |
| 3.2 | The IAP policy mode is agreed: `DRY_RUN` with a review date, or `ENFORCE` | `terraform output iap_enforcement_mode` | | |
| 3.3 | `scripts/check_tool_policy.sh` passes for every MCP server | `TOOL_POLICY: PASS (...)` | | |
| 3.4 | `scripts/discover.sh` shows no existing agent outside the governed path, or each one has a lateral plan | Markdown report attached | | |
| 3.5 | The known audit gap is accepted: with IAP policy V2, a denied call writes no `403` row and no IAP `tools/call` entry | Sign-off | | |

## 4. Operations

| # | Check | How to check | Owner | Result |
|---|---|---|---|---|
| 4.1 | Runbooks are read by the operations team: `add_agent.md`, `switch_policy_mode.md`, `teardown.md` | Names and dates | | |
| 4.2 | Who can run `terraform apply` is agreed, and the agent harness guard (`.agents/hooks.json`) is in place | Access list | | |
| 4.3 | Log retention of `<name_prefix>-agent-audit` matches the customer retention rule | `log_retention_days` value | | |
| 4.4 | Emergency contacts and the escalation path for the gateway, IAP, and Model Armor are written down | Contact list | | |
| 4.5 | A teardown plan exists: `scripts/teardown_plan.sh --intent production` reviewed | `TEARDOWN_PLAN:` line attached | | |

## Sign-off

| Role | Name | Date |
|---|---|---|
| Build team | | |
| Operations team | | |
| Security owner | | |
