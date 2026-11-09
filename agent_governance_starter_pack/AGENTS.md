# Agent Rules for Agent Governance Starter Pack

These rules apply to any automated agent or CLI harness that runs in `agent_governance_starter_pack/`.

## Safety Rules

1. Operate on one sandbox project only: the `project_id` configured in `terraform/terraform.tfvars`.
1. Use only the skills in `.agents/skills/` and the files in this folder. Do not load user-level skills (for example from `~/.gemini/skills/` or `~/.gemini/config/skills/`), and do not read files outside this folder. Do not add environment variables or flags that a skill in this folder does not name.
1. During a long command (`terraform apply`, `terraform destroy`, `scripts/cleanup.sh`, or a wait for a policy to apply), report progress to the user every 5 minutes without being asked: the elapsed time, the last completed step from the command output, and the step that runs now. Most of the time goes to Agent Gateway create and delete (about 3 to 5 minutes each).
1. Run Terraform with `terraform -chdir=terraform ...`. Do not start a command with `cd`. A CLI permission rule that matches the start of a command then names `terraform`, not `cd`. Tell the user to approve `terraform` commands once only, because a rule for all commands that start with `terraform` also allows `apply` and `destroy`.
1. Never pipe input into a script to answer its prompt (for example `echo PROJECT_ID | scripts/cleanup.sh` or `yes | ...`). Use the flag that the skill names, after the user approves.
2. Never modify organization-level policies or resources outside the target project.
3. Run `scripts/preflight.sh` before any Terraform plan or apply. Stop immediately if the report status is `NO_GO`.
4. Never run `terraform apply` or `terraform destroy` without human approval of the plan summary (resource counts and resource types).
5. On any permission error, credential error, or organization policy violation, stop immediately and report the exact command or prerequisite needed. Do not retry blindly.
6. Never commit real project IDs, project numbers, organization IDs, customer names, or internal URLs to git.

## Headless Mode

Headless CLI runs (for example, `agy -p "<prompt>" --output-format json`) are permitted only for read-only tasks (`geap-preflight` and `terraform plan`). Note: the `agy` CLI flags are not verified against public documentation yet. The same rule applies to Claude Code headless runs (`claude -p "<prompt>" --output-format json`). Claude Code reads these rules through the `@AGENTS.md` import in `CLAUDE.md`.

## Skills

| Skill | Path | Purpose |
|---|---|---|
| `geap-discover` | `.agents/skills/geap-discover/SKILL.md` | Read-only scan of an existing project and the lateral steps for each tier |
| `geap-configure` | `.agents/skills/geap-configure/SKILL.md` | Ask the user for the project, region, name prefix, governance tier, domain restricted sharing approach, and IAP mode, then write `terraform/terraform.tfvars` |
| `geap-preflight` | `.agents/skills/geap-preflight/SKILL.md` | Run `scripts/preflight.sh` and inspect the JSON readiness report |
| `geap-deploy` | `.agents/skills/geap-deploy/SKILL.md` | Package the agent, run offline tests, run `terraform plan`, and wait for human approval before `terraform apply` |
| `geap-verify` | `.agents/skills/geap-verify/SKILL.md` | Test the deployed agent, Model Armor, IAP enforcement, and audit logs |
| `geap-reset` | `.agents/skills/geap-reset/SKILL.md` | Switch `iap_enforcement_mode` back to `DRY_RUN` and reset the sample MCP server state |
| `geap-teardown` | `.agents/skills/geap-teardown/SKILL.md` | Destroy all Terraform resources and sweep any out-of-state GEAP resources in the target project |
