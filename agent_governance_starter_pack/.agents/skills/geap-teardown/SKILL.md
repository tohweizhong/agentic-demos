---
name: geap-teardown
description: Tear down all agent governance starter pack resources in the target project and sweep any out-of-state resources.
---

# Skill: geap-teardown

Reset the target project by destroying all Terraform-managed resources and sweeping any out-of-state GEAP resources, IAM bindings, and temporary build artifacts.

## Safety Gate

Never run `scripts/cleanup.sh` or `terraform destroy` without explicit human confirmation of the target `project_id`.

Never pipe input into `scripts/cleanup.sh` (for example `echo PROJECT_ID | scripts/cleanup.sh`). The script refuses piped input. Pass `--confirm <PROJECT_ID>` only after the user approves, so that the CLI shows the full command for approval.

## Steps

1. Read `project_id`, `region`, and `name_prefix` from `terraform/terraform.tfvars` (or `terraform output`).
2. Ask the user what they plan next, with these options: deploy again later from this clone (`redeploy`), sandbox or rehearsal that is finished (`done`), or customer production (`production`).
3. Run the read-only plan script and show its `TEARDOWN_PLAN:` line word for word. It reads the Terraform state and the log bucket state, and it recommends the log bucket flag:
   ```bash
   scripts/teardown_plan.sh --intent <redeploy|done|production>
   ```
   Recommend the command in that line. Do not recommend a flag from your own judgment. Add `--include-project-wide` only if the user confirms that the project holds the starter pack and nothing else. [runbooks/teardown.md](../../../runbooks/teardown.md) lists what each step deletes.
4. Show the target `project_id`, `region`, prefix, and the full command, and ask for explicit confirmation. After the user confirms, run the command and add `--confirm <PROJECT_ID>`. Run it as a background task. Every 5 minutes, report the elapsed time, the resources that the output shows as deleted, and the step that runs now. A full teardown with gateways takes about 25 minutes.
   If the script ends with `Clean-up NOT complete`, report the errors and run it again after the user agrees.
5. Run `scripts/preflight.sh --project <PROJECT_ID> --region <REGION>` to verify that `terraform_state_resource_count` is `0` and no leftover gateways, Reasoning Engines, or Cloud Run services remain.
