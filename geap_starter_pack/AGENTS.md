# Agent Rules for GEAP Starter Pack

These rules apply to any automated agent or CLI harness that runs in `geap_starter_pack/`.

## Safety Rules

1. Operate on one sandbox project only: the `project_id` configured in `terraform/terraform.tfvars`.
2. Never modify organization-level policies or resources outside the target project.
3. Run `scripts/preflight.sh` before any Terraform plan or apply. Stop immediately if the report status is `NO_GO`.
4. Never run `terraform apply` or `terraform destroy` without human approval of the plan summary (resource counts and resource types).
5. On any permission error, credential error, or organization policy violation, stop immediately and report the exact command or prerequisite needed. Do not retry blindly.
6. Never commit real project IDs, project numbers, organization IDs, customer names, or internal URLs to git.

## Headless Mode

Headless CLI runs (for example, `agy -p "<prompt>" --output-format json`) are permitted only for read-only tasks (`geap-preflight` and `terraform plan`). Note: the `agy` CLI flags are not verified against public documentation yet.

## Skills

| Skill | Path | Purpose |
|---|---|---|
| `geap-preflight` | `.agents/skills/geap-preflight/SKILL.md` | Run `scripts/preflight.sh` and inspect the JSON readiness report |
| `geap-deploy` | `.agents/skills/geap-deploy/SKILL.md` | Package the agent, run offline tests, run `terraform plan`, and wait for human approval before `terraform apply` |
| `geap-verify` | `.agents/skills/geap-verify/SKILL.md` | Test the deployed agent, Model Armor, IAP enforcement, and audit logs |
| `geap-doctor` | `.agents/skills/geap-doctor/SKILL.md` | Check live governance posture across all 5 tiers and detect ungoverned (rogue) agents |
| `geap-audit-tools` | `.agents/skills/geap-audit-tools/SKILL.md` | Verify that every non-read-only MCP tool in `mcp-server/tool_spec.json` is governed in `policies/iap_access_policy.yaml` |
| `geap-reset` | `.agents/skills/geap-reset/SKILL.md` | Switch `iap_enforcement_mode` back to `DRY_RUN` and reset the sample MCP server state |
| `geap-teardown` | `.agents/skills/geap-teardown/SKILL.md` | Destroy all Terraform resources and sweep any out-of-state GEAP resources in the target project |
