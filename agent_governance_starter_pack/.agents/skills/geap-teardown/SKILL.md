---
name: geap-teardown
description: Tear down all agent governance starter pack resources in the target project and sweep any out-of-state resources.
---

# Skill: geap-teardown

Reset the target project by destroying all Terraform-managed resources and sweeping any out-of-state GEAP resources, IAM bindings, and temporary build artifacts.

## Safety Gate

Never run `scripts/cleanup.sh` or `terraform destroy` without explicit human confirmation of the target `project_id`.

## Steps

1. Read `project_id`, `region`, and `name_prefix` from `terraform/terraform.tfvars` (or `terraform output`).
2. Show the target `project_id` and `region` to the user and ask for explicit confirmation to tear down all agent governance starter pack resources in that project.
3. After the user confirms, run `scripts/cleanup.sh --project <PROJECT_ID> --region <REGION>` (pass `--keep-log-bucket` by default so the regional Cloud Logging bucket is not locked in `DELETE_REQUESTED` state for 7 days, or pass `--purge-all` if the user wants the log bucket soft-deleted too). Add `--include-project-wide` only if the user confirms that the project holds the starter pack and nothing else. [runbooks/teardown.md](../../../runbooks/teardown.md) lists what each step deletes.
   If the script ends with `Clean-up NOT complete`, report the errors and run it again after the user agrees.
4. Run `scripts/preflight.sh --project <PROJECT_ID> --region <REGION>` to verify that `terraform_state_resource_count` is `0` and no leftover gateways, Reasoning Engines, or Cloud Run services remain.
